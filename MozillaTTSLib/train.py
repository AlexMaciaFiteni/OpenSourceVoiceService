import os
import sys
import time
import shutil
import torch
import argparse
import importlib
import traceback
import numpy as np

import torch.nn as nn
from torch import optim
from torch.utils.data import DataLoader
from tensorboardX import SummaryWriter

from utils.generic_utils import (
    remove_experiment_folder, create_experiment_folder, save_checkpoint,
    save_best_model, load_config, lr_decay, count_parameters, check_update,
    get_commit_hash, sequence_mask, NoamLR)
from utils.text.symbols import symbols, phonemes
from utils.visual import plot_alignment, plot_spectrogram
from models.tacotron import Tacotron
from layers.losses import L1LossMasked
from datasets.TTSDataset import MyDataset
from utils.audio import AudioProcessor
from utils.synthesis import synthesis
from utils.logger import Logger

torch.manual_seed(1)
use_cuda = torch.cuda.is_available()
print(" > Using CUDA: ", use_cuda)
print(" > Number of GPUs: ", torch.cuda.device_count())


def setup_loader(is_val=False):
    global ap
    if is_val and not c.run_eval:
        loader = None
    else:
        dataset = MyDataset(
            c.data_path,
            c.meta_file_val if is_val else c.meta_file_train,
            c.r,
            c.text_cleaner,
            preprocessor=preprocessor,
            ap=ap,
            batch_group_size=0 if is_val else 8 * c.batch_size,
            min_seq_len=0 if is_val else c.min_seq_len,
            max_seq_len=float("inf") if is_val else c.max_seq_len,
            cached=False if c.dataset != "tts_cache" else True,
            phoneme_cache_path=c.phoneme_cache_path,
            use_phonemes=c.use_phonemes,
            phoneme_language=c.phoneme_language
            )
        loader = DataLoader(
            dataset,
            batch_size=c.eval_batch_size if is_val else c.batch_size,
            shuffle=False,
            collate_fn=dataset.collate_fn,
            drop_last=False,
            num_workers=c.num_val_loader_workers if is_val else c.num_loader_workers,
            pin_memory=False)
    return loader


def train(model, criterion, criterion_st, optimizer, optimizer_st,
          scheduler, ap, epoch):
    data_loader = setup_loader(is_val=False)
    model.train()
    epoch_time = 0
    avg_linear_loss = 0
    avg_mel_loss = 0
    avg_stop_loss = 0
    avg_step_time = 0
    print(" | > Epoch {}/{}".format(epoch, c.epochs), flush=True)
    n_priority_freq = int(
        3000 / (c.audio['sample_rate'] * 0.5) * c.audio['num_freq'])
    batch_n_iter = int(len(data_loader.dataset) / c.batch_size)
    for num_iter, data in enumerate(data_loader):
        start_time = time.time()

        # setup input data
        text_input = data[0]
        text_lengths = data[1]
        linear_input = data[2]
        mel_input = data[3]
        mel_lengths = data[4]
        stop_targets = data[5]
        avg_text_length = torch.mean(text_lengths.float())
        avg_spec_length = torch.mean(mel_lengths.float())

        # set stop targets view, we predict a single stop token per r frames prediction
        stop_targets = stop_targets.view(text_input.shape[0],
                                         stop_targets.size(1) // c.r, -1)
        stop_targets = (stop_targets.sum(2) > 0.0).unsqueeze(2).float()

        current_step = num_iter + args.restore_step + \
            epoch * len(data_loader) + 1

        # setup lr
        if c.lr_decay:
            scheduler.step()
        optimizer.zero_grad()
        optimizer_st.zero_grad()

        # dispatch data to GPU
        if use_cuda:
            text_input = text_input.cuda(non_blocking=True)
            text_lengths = text_lengths.cuda(non_blocking=True)
            mel_input = mel_input.cuda(non_blocking=True)
            mel_lengths = mel_lengths.cuda(non_blocking=True)
            linear_input = linear_input.cuda(non_blocking=True)
            stop_targets = stop_targets.cuda(non_blocking=True)

        # compute mask for padding
        mask = sequence_mask(text_lengths)

        # forward pass
        if use_cuda:
            mel_output, linear_output, alignments, stop_tokens = torch.nn.parallel.data_parallel(
                model, (text_input, mel_input, mask))
        else:
            mel_output, linear_output, alignments, stop_tokens = model(
                text_input, mel_input, mask)

        # loss computation
        stop_loss = criterion_st(stop_tokens, stop_targets)
        mel_loss = criterion(mel_output, mel_input, mel_lengths)
        linear_loss = (1 - c.loss_weight) * criterion(linear_output, linear_input, mel_lengths)\
            + c.loss_weight * criterion(linear_output[:, :, :n_priority_freq],
                              linear_input[:, :, :n_priority_freq],
                              mel_lengths)
        loss = mel_loss + linear_loss

        # backpass and check the grad norm for spec losses
        loss.backward(retain_graph=True)
        # custom weight decay
        for group in optimizer.param_groups:
            for param in group['params']:
                current_lr = group['lr']
                param.data = param.data.add(-c.wd * group['lr'], param.data)
        grad_norm, skip_flag = check_update(model, 1)
        if skip_flag:
            optimizer.zero_grad()
            print("   | > Iteration skipped!!", flush=True)
            continue
        optimizer.step()

        # backpass and check the grad norm for stop loss
        stop_loss.backward()
        # custom weight decay
        for group in optimizer_st.param_groups:
            for param in group['params']:
                param.data = param.data.add(-c.wd * group['lr'], param.data)
        grad_norm_st, skip_flag = check_update(model.decoder.stopnet, 0.5)
        if skip_flag:
            optimizer_st.zero_grad()
            print("   | > Iteration skipped fro stopnet!!")
            continue
        optimizer_st.step()

        step_time = time.time() - start_time
        epoch_time += step_time

        if current_step % c.print_step == 0:
            print(
                "   | > Step:{}/{}  GlobalStep:{}  TotalLoss:{:.5f}  LinearLoss:{:.5f}  "
                "MelLoss:{:.5f}  StopLoss:{:.5f}  GradNorm:{:.5f}  "
                "GradNormST:{:.5f}  AvgTextLen:{:.1f}  AvgSpecLen:{:.1f}  StepTime:{:.2f}  LR:{:.6f}".format(
                    num_iter, batch_n_iter, current_step, loss.item(),
                    linear_loss.item(), mel_loss.item(), stop_loss.item(),
                    grad_norm, grad_norm_st, avg_text_length, avg_spec_length, step_time, current_lr),
                flush=True)

        avg_linear_loss += float(linear_loss.item())
        avg_mel_loss += float(mel_loss.item())
        avg_stop_loss += stop_loss.item()
        avg_step_time += step_time

        # Plot Training Iter Stats
        iter_stats = {"loss_posnet": linear_loss.item(),
                      "loss_decoder": mel_loss.item(),
                      "lr": current_lr,
                      "grad_norm": grad_norm,
                      "grad_norm_st": grad_norm_st,
                      "step_time": step_time}
        tb_logger.tb_train_iter_stats(current_step, iter_stats)

        if current_step % c.save_step == 0:
            if c.checkpoint:
                # save model
                save_checkpoint(model, optimizer, optimizer_st,
                                linear_loss.item(), OUT_PATH, current_step,
                                epoch)

            # Diagnostic visualizations
            const_spec = linear_output[0].data.cpu().numpy()
            gt_spec = linear_input[0].data.cpu().numpy()
            align_img = alignments[0].data.cpu().numpy()

            figures = {"prediction": plot_spectrogram(const_spec, ap),
                       "ground_truth": plot_spectrogram(gt_spec, ap),
                       "alignment": plot_alignment(align_img)}
            tb_logger.tb_train_figures(current_step, figures)

            # Sample audio
            tb_logger.tb_train_audios(current_step, 
                                        {'TrainAudio': ap.inv_spectrogram(const_spec.T)},
                                        c.audio["sample_rate"])

    avg_linear_loss /= (num_iter + 1)
    avg_mel_loss /= (num_iter + 1)
    avg_stop_loss /= (num_iter + 1)
    avg_total_loss = avg_mel_loss + avg_linear_loss + avg_stop_loss
    avg_step_time /= (num_iter + 1)

    # print epoch stats
    print(
        "   | > EPOCH END -- GlobalStep:{}  AvgTotalLoss:{:.5f}  "
        "AvgLinearLoss:{:.5f}  AvgMelLoss:{:.5f}  "
        "AvgStopLoss:{:.5f}  EpochTime:{:.2f}  "
        "AvgStepTime:{:.2f}".format(current_step, avg_total_loss,
                                    avg_linear_loss, avg_mel_loss,
                                    avg_stop_loss, epoch_time, avg_step_time),
        flush=True)

    # Plot Training Epoch Stats
    epoch_stats = {"loss_postnet": avg_linear_loss,
                   "loss_decoder": avg_mel_loss,
                   "stop_loss": avg_stop_loss,
                   "epoch_time": epoch_time}
    tb_logger.tb_train_epoch_stats(current_step, epoch_stats)
    if c.tb_model_param_stats:
        tb_logger.tb_model_weights(model, current_step) 
    return avg_linear_loss, current_step


def evaluate(model, criterion, criterion_st, ap, current_step):
    data_loader = setup_loader(is_val=True)
    model.eval()
    epoch_time = 0
    avg_linear_loss = 0
    avg_mel_loss = 0
    avg_stop_loss = 0
    print(" | > Validation")
    test_sentences = [
        "It took me quite a long time to develop a voice, and now that I have it I'm not going to be silent.",
        "Be a voice, not an echo.",
        "I'm sorry Dave. I'm afraid I can't do that.",
        "This cake is great. It's so delicious and moist."
    ]
    n_priority_freq = int(
        3000 / (c.audio['sample_rate'] * 0.5) * c.audio['num_freq'])
    with torch.no_grad():
        if data_loader is not None:
            for num_iter, data in enumerate(data_loader):
                start_time = time.time()

                # setup input data
                text_input = data[0]
                text_lengths = data[1]
                linear_input = data[2]
                mel_input = data[3]
                mel_lengths = data[4]
                stop_targets = data[5]

                # set stop targets view, we predict a single stop token per r frames prediction
                stop_targets = stop_targets.view(text_input.shape[0],
                                                 stop_targets.size(1) // c.r,
                                                 -1)
                stop_targets = (stop_targets.sum(2) > 0.0).unsqueeze(2).float()

                # dispatch data to GPU
                if use_cuda:
                    text_input = text_input.cuda()
                    mel_input = mel_input.cuda()
                    mel_lengths = mel_lengths.cuda()
                    linear_input = linear_input.cuda()
                    stop_targets = stop_targets.cuda()

                # forward pass
                mel_output, linear_output, alignments, stop_tokens =\
                    model.forward(text_input, mel_input)

                # loss computation
                stop_loss = criterion_st(stop_tokens, stop_targets)
                mel_loss = criterion(mel_output, mel_input, mel_lengths)
                linear_loss = 0.5 * criterion(linear_output, linear_input, mel_lengths) \
                    + 0.5 * criterion(linear_output[:, :, :n_priority_freq],
                                    linear_input[:, :, :n_priority_freq],
                                    mel_lengths)
                loss = mel_loss + linear_loss + stop_loss

                step_time = time.time() - start_time
                epoch_time += step_time

                if num_iter % c.print_step == 0:
                    print(
                        "   | > TotalLoss: {:.5f}   LinearLoss: {:.5f}   MelLoss:{:.5f}  "
                        "StopLoss: {:.5f}  ".format(loss.item(),
                                                    linear_loss.item(),
                                                    mel_loss.item(),
                                                    stop_loss.item()),
                        flush=True)

                avg_linear_loss += float(linear_loss.item())
                avg_mel_loss += float(mel_loss.item())
                avg_stop_loss += stop_loss.item()

            # Diagnostic visualizations
            idx = np.random.randint(mel_input.shape[0])
            const_spec = linear_output[idx].data.cpu().numpy()
            gt_spec = linear_input[idx].data.cpu().numpy()
            align_img = alignments[idx].data.cpu().numpy()

            eval_figures = {"prediction": plot_spectrogram(const_spec, ap),
                            "ground_truth": plot_spectrogram(gt_spec, ap),
                            "alignment": plot_alignment(align_img)}
            tb_logger.tb_eval_figures(current_step, eval_figures)

            # Sample audio
            tb_logger.tb_eval_audios(current_step, {"ValAudio": ap.inv_spectrogram(const_spec.T)}, c.audio["sample_rate"])

            # compute average losses
            avg_linear_loss /= (num_iter + 1)
            avg_mel_loss /= (num_iter + 1)
            avg_stop_loss /= (num_iter + 1)

            # Plot Validation Stats
            epoch_stats = {"loss_postnet": avg_linear_loss,
                           "loss_decoder": avg_mel_loss,
                           "stop_loss": avg_stop_loss}
            tb_logger.tb_eval_stats(current_step, epoch_stats)

    # test sentences
    test_audios = {}
    test_figures = {}
    for idx, test_sentence in enumerate(test_sentences):
        try:
            wav, alignment, linear_spec, _, stop_tokens = synthesis(
                model, test_sentence, c, use_cuda, ap)
            file_path = os.path.join(AUDIO_PATH, str(current_step))
            os.makedirs(file_path, exist_ok=True)
            file_path = os.path.join(file_path,
                                     "TestSentence_{}.wav".format(idx))
            ap.save_wav(wav, file_path)
            test_audios['{}-audio'.format(idx)] = wav
            test_figures['{}-prediction'.format(idx)] = plot_spectrogram(linear_spec, ap)
            test_figures['{}-alignment'.format(idx)] = plot_alignment(alignment)
        except:
            print(" !! Error creating Test Sentence -", idx)
            traceback.print_exc()
    tb_logger.tb_test_audios(current_step, test_audios, c.audio['sample_rate'])    
    tb_logger.tb_test_figures(current_step, test_figures)
    return avg_linear_loss


def main(args):
    num_chars = len(phonemes) if c.use_phonemes else len(symbols)
    model = Tacotron(num_chars, c.embedding_size, ap.num_freq, ap.num_mels, c.r, c.memory_size)
    print(" | > Num output units : {}".format(ap.num_freq), flush=True)

    optimizer = optim.Adam(model.parameters(), lr=c.lr, weight_decay=0)
    optimizer_st = optim.Adam(
        model.decoder.stopnet.parameters(), lr=c.lr, weight_decay=0)

    criterion = L1LossMasked()
    criterion_st = nn.BCELoss()

    partial_init_flag = False
    if args.restore_path:
        checkpoint = torch.load(args.restore_path)
        try:
            model.load_state_dict(checkpoint['model'])
        except:
            print(" > Partial model initialization.")
            partial_init_flag = True
            model_dict = model.state_dict()
            # Partial initialization: if there is a mismatch with new and old layer, it is skipped.
            # 1. filter out unnecessary keys
            pretrained_dict = {
                k: v
                for k, v in checkpoint['model'].items() if k in model_dict 
            }
            # 2. filter out different size layers
            pretrained_dict = {
                k: v
                for k, v in checkpoint['model'].items() if v.numel() == model_dict[k].numel()
            }
            # 3. overwrite entries in the existing state dict
            model_dict.update(pretrained_dict)
            # 4. load the new state dict
            model.load_state_dict(model_dict)
            print(" | > {} / {} layers are initialized".format(len(pretrained_dict), len(model_dict)))
        if use_cuda:
            model = model.cuda()
            criterion.cuda()
            criterion_st.cuda()
        if not partial_init_flag:
            optimizer.load_state_dict(checkpoint['optimizer'])
        for group in optimizer.param_groups:
                group['lr'] = c.lr
        print(
            " > Model restored from step %d" % checkpoint['step'], flush=True)
        start_epoch = checkpoint['epoch']
        best_loss = checkpoint['linear_loss']
        args.restore_step = checkpoint['step']
    else:
        args.restore_step = 0
        print("\n > Starting a new training", flush=True)
        if use_cuda:
            model = model.cuda()
            criterion.cuda()
            criterion_st.cuda()

    if c.lr_decay:
        scheduler = NoamLR(
            optimizer,
            warmup_steps=c.warmup_steps,
            last_epoch=args.restore_step - 1)
    else:
        scheduler = None

    num_params = count_parameters(model)
    print(" | > Model has {} parameters".format(num_params), flush=True)

    if not os.path.exists(CHECKPOINT_PATH):
        os.mkdir(CHECKPOINT_PATH)

    if 'best_loss' not in locals():
        best_loss = float('inf')

    for epoch in range(0, c.epochs):
        train_loss, current_step = train(model, criterion, criterion_st,
                                         optimizer, optimizer_st,
                                         scheduler, ap, epoch)
        val_loss = evaluate(model, criterion, criterion_st, ap,
                            current_step)
        print(
            " | > Train Loss: {:.5f}   Validation Loss: {:.5f}".format(
                train_loss, val_loss),
            flush=True)
        target_loss = train_loss
        if c.run_eval:
            target_loss = val_loss
        best_loss = save_best_model(model, optimizer, target_loss, best_loss,
                                    OUT_PATH, current_step, epoch)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--restore_path',
        type=str,
        help='Path to model outputs (checkpoint, tensorboard etc.).',
        default=0)
    parser.add_argument(
        '--config_path',
        type=str,
        help='Path to config file for training.',
    )
    parser.add_argument(
        '--debug',
        type=bool,
        default=False,
        help='Do not verify commit integrity to run training.')
    parser.add_argument(
        '--data_path', type=str, default='', help='Defines the data path. It overwrites config.json.')
    args = parser.parse_args()

    # setup output paths and read configs
    c = load_config(args.config_path)
    _ = os.path.dirname(os.path.realpath(__file__))
    OUT_PATH = os.path.join(_, c.output_path)
    OUT_PATH = create_experiment_folder(OUT_PATH, c.model_name, args.debug)
    CHECKPOINT_PATH = os.path.join(OUT_PATH, 'checkpoints')
    AUDIO_PATH = os.path.join(OUT_PATH, 'test_audios')
    os.makedirs(AUDIO_PATH, exist_ok=True)
    shutil.copyfile(args.config_path, os.path.join(OUT_PATH, 'config.json'))

    if args.data_path != '':
        c.data_path = args.data_path

    # setup tensorboard
    LOG_DIR = OUT_PATH
    tb_logger = Logger(LOG_DIR)

    # Conditional imports
    preprocessor = importlib.import_module('datasets.preprocess')
    preprocessor = getattr(preprocessor, c.dataset.lower())
    audio = importlib.import_module('utils.' + c.audio['audio_processor'])
    AudioProcessor = getattr(audio, 'AudioProcessor')

    # Audio processor
    ap = AudioProcessor(**c.audio)

    try:
        main(args)
    except KeyboardInterrupt:
        remove_experiment_folder(OUT_PATH)
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception:
        remove_experiment_folder(OUT_PATH)
        traceback.print_exc()
        sys.exit(1)

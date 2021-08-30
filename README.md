# OpenSourceVoiceSevice
Este repositorio contiene el código que se ejecuta en el SAM Voice Service. Se encarga de recibir órdenes en forma de audio, de convertirlas a texto con su módulo ASR (Mozilla DeepSpeech), de usar ese texto para mantener la conversación con un asistente inteligente (Hecho con Rasa), y de convertir la respuesta de dicho asistente a audio de nuevo con su módulo TTS (Mozilla TTS).

En este repositorio no se incluyen los modelos de voz para ASR y TTS ya que pesan demasiado para subirlos.

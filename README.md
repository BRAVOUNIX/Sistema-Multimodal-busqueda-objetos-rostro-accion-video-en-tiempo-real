# Nova Desktop System

Sistema de escritorio con visión por computadora y LLMs
El sistema es multimodal porque utiliza varios modelos en su arquitectura como yolov8, st_gcn,facenet, API Chatgpt
El sistema permite buscar:
- Por Objeto, Objeto y color . Utiliza las mismas clase de Yolov8
- Por Rostro, utilizando yolov8 con facenet utilizando una carpeta como repositorio de imaganes de rostros previamente registrados en sistema.
- Por Accion, utilizando yolov8 con ST_GCN (Spatial-Temporal Graph Convolutional Networks)

## Requisitos
- Python 3.12
- PostgreSQL
- Conda

## Instalación
```bash
conda env create -f environment.yml
conda activate nova-desktop
```

## Login del sistema
![Login del sistema](img/login.JPG)

## Registro de Usuarios del sistema con perfil Administrador u Operador
![Registro Usuario](img/registro_usuarios.JPG)

## Registro de Rostro a Buscar
![Registro Rostro](img/registro_rostro.JPG)

## Busqueda de Objeto
![Busqueda Objeto](img/objeto.JPG)

## Busqueda de Rostro
![Busqueda Rostro](img/rostro.JPG)

## Busqueda de Acción
![Busqueda Accion](img/accion.JPG)

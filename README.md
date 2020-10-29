# ideuy-py

Paquete de Python para descargar ortoimágenes de
[IDEuy](https://www.gub.uy/infraestructura-datos-espaciales/).

## Instalación

El paquete se puede instalar con pip, ejecutando desde una terminal:

```
pip install --user ideuy
```

## Uso

### Scripts de consola disponibles

* `ideuy_filter`: Filtra un shapefile de grilla con otro shapefile de Áreas de Interés (AOI).
* `ideuy_download_images`: Descarga las imágenes del vuelo basado en un shapefile de grilla.

## Desarrollo

Crear un entorno virtual e instalar el paquete con pip en modo desarrollo, por ejemplo:

```
virtualenv -p python3 .venv/
source .venv/bin/activate
pip install -e .
```

## Licencia

Ver [LICENSE.txt](LICENSE.txt).

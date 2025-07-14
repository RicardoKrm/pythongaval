# TMS Gaval

Este es un sistema de gestión de flotas (TMS) desarrollado en Django.

## Requisitos

*   Python 3.12 o superior
*   PostgreSQL 14 o superior

## Instalación

1.  **Clona el repositorio:**

    ```bash
    git clone https://github.com/tu-usuario/tu-repositorio.git
    cd tu-repositorio
    ```

2.  **Crea y activa un entorno virtual:**

    ```bash
    python -m venv venv
    source venv/bin/activate # En Windows: venv\Scripts\activate
    ```

3.  **Instala las dependencias:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configura la base de datos:**

    *   Asegúrate de que PostgreSQL esté instalado y en ejecución.
    *   Crea una base de datos y un usuario para el proyecto:

        ```sql
        CREATE DATABASE tms_gaval_db;
        CREATE USER tms_user WITH PASSWORD 'karma627';
        GRANT ALL PRIVILEGES ON DATABASE tms_gaval_db TO tms_user;
        ```

5.  **Configura las variables de entorno:**

    *   Crea un archivo `.env` en la raíz del proyecto. Puedes copiar el archivo `.env.example` y renombrarlo a `.env`:

        ```bash
        cp .env.example .env
        ```

    *   Abre el archivo `.env` y modifica las variables según tu configuración local.

6.  **Aplica las migraciones:**

    ```bash
    python manage.py migrate_schemas --shared
    ```

7.  **Crea un tenant:**

    ```bash
    python manage.py create_tenant --schema_name=gaval --nombre=Gaval --razon_social="Gaval SpA" --domain-domain=gaval.localhost --noinput
    ```

8.  **Crea un superusuario:**

    ```bash
    python manage.py create_tenant_superuser --schema=gaval
    ```

9.  **Ejecuta el servidor de desarrollo:**

    ```bash
    python manage.py runserver
    ```

10. **Agrega el dominio del tenant a tu archivo de hosts:**

    *   Abre tu archivo de hosts (`/etc/hosts` en Linux/macOS, `C:\Windows\System32\drivers\etc\hosts` en Windows) y agrega la siguiente línea:

        ```
        127.0.0.1 gaval.localhost
        ```

11. **Accede a la aplicación:**

    *   Abre tu navegador y ve a `http://gaval.localhost:8000`.

## Carga Masiva de Datos

El proyecto incluye una funcionalidad de carga masiva de datos a través de archivos de Excel. Puedes encontrar las plantillas en el directorio `plantillas/`.

Para usar la carga masiva:

1.  Ve a la sección de "Carga Masiva" en la aplicación.
2.  Selecciona el archivo de Excel que quieres cargar.
3.  Haz clic en "Cargar".

Las plantillas disponibles son:

*   `plantilla_vehiculos.xlsx`
*   `plantilla_pautas.xlsx`
*   `plantilla_repuestos.xlsx`
*   `plantilla_historial_mantenimiento.xlsx`
*   `plantilla_bitacoras_diarias.xlsx`

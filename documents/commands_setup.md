Secuencia de Comandos para Ejecutar una App Flask en un Entorno Virtual
Asegúrate de tener Git y Python instalados en tu máquina (incluyendo pip). Usa la terminal integrada en Visual Studio Code (presiona Ctrl + ` o ve a Terminal > New Terminal) para ejecutar estos comandos.


1 - Clona el repositorio de GitHub:


2 - Crea un entorno virtual (virtual environment):

     python -m venv venv

    (Esto crea una carpeta llamada venv. Puedes usar otro nombre si prefieres.)

3 - Activa el entorno virtual:
  

    En Windows:      venv\Scripts\activate

    En macOS/Linux:  source venv/bin/activate
    
    (Verás (venv) al inicio de la línea de comandos, indicando que está activo.)

4 - Instala las dependencias del proyecto:

    pip install -r requirements.txt

    (Si no hay requirements.txt, instala Flask manualmente: pip install flask y otras librerías necesarias.)


5 - Ejecuta la app Flask:
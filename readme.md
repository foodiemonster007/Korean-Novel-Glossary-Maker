### Credits: Foodiemonster007

# About

This tool helps you create a translation glossary spreadsheet for Korean novels, to improve the quality of your machine translations.



# Requirements

1. **Download** all the files in this repository into a folder on your pc.

2. **Python**: This is a programming language that makes the tool work. You'll need to install it from the official website (https://www.python.org/downloads/). Make sure to check the 2 boxes that say "Add Python to PATH" and "pip" during installation. This step lets your computer easily find and run the program.

3. **Google Cloud Project**: Go to [console.cloud.google.com](https://console.cloud.google.com) and sign in with your Google account. Click the project dropdown at the top of the page and click **"New Project"**. Give it any name you like and click **"Create"**. Once created, select your new project. Your **Project ID** is shown under the project name (it looks like `my-project-name-123456`). Copy it. In the left sidebar, go to **APIs & Services → Library**, search for **"Vertex AI API"** and click **Enable**.

4. **Enable Vertex API:** Go to https://console.cloud.google.com/apis/library/aiplatform.googleapis.com. Download and install gcloud from https://cloud.google.com/sdk/docs/install. Open a new command prompt terminal and run: 

  > gcloud auth application-default login

5. **Run "setup.py"** by double-clicking it before you proceed to ensure everything is properly set up. You only ever need to run it ONCE. You should see the message "SETUP SUCCESSFUL!" in the command prompt window that pops up.

6. **(optional) Local Trained Model**: You will need to download a 3 GB file to use the local model (and save AI credits). The download link is: https://mega.nz/file/MvgFGDJJ#YdQxyWAHsBxNGZoraBn336QG5c46gNE18WglfHuzrnc

	

# Instructions

1. Put your novel chapter raws in .txt file format inside a folder and copy it into the main directory. I have provided a folder named "raws" as an example.

2. Start the Program: Find the program file called GLOSSARY_MAKER.py and double click it.

3. Enter Your API Key: When the program opens, you will see that the API key field is blank. You need to fill it with the Google API key you got earlier. This is a crucial step; the tool won't work without it.

4. Configure your custom settings and then hit RUN NOVEL GLOSSARY MAKER to run the code and create your novel translation glossary. Refer to READ ME.pdf to see what each setting does.




# Instructions for Google Colab

You can run this tool is in your browser with Google Colab. No installation is needed but there is no GUI.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/foodiemonster007/Korean-Novel-Glossary-Maker/blob/main/korean_glossary_maker_colab.ipynb)

### Step 1: Create a Google Cloud Project
1. Go to [console.cloud.google.com](https://console.cloud.google.com) and sign in with your Google account.
2. Click the project dropdown at the top of the page and click **"New Project"**.
3. Give it any name you like and click **"Create"**.
4. Once created, select your new project. Your **Project ID** is shown under the project name (it looks like `my-project-name-123456`). Copy it.
5. In the left sidebar, go to **APIs & Services → Library**, search for **"Agent Platform API"** and click **Enable**.

### Step 2: Add your Project ID to Colab
1. Click the "Open in Colab" button above.
2. In the left sidebar, click the **🔑 key icon** (says "Secrets" on hover).
3. Click **"+ Add new secret"**.
4. In the **Name** field, type exactly: `GOOGLE_CLOUD_PROJECT`
5. In the **Value** field, paste your Project ID (e.g. `my-project-name-123456`).
6. Toggle **"Notebook access"** to ON and click **Save**.

### Step 3: Run
1. Run the notebook cells in order. When prompted, sign in with the same Google account you used to create the project.
2. Upload your Korean novel `.txt` files when prompted (one file per chapter).
3. Download your finished `glossary.xlsx` file!



# Frequently Asked Questions


1. If pip is missing: Uninstall and reinstall python, remember to check the boxes for "pip" and "Add Python to PATH"

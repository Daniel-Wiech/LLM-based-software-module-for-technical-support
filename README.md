# Technical Support Module with LLM Integration

This project implements a **technical support module** using **Large Language Models (LLM)** and a **PostgreSQL SQL database**. It provides a backend API, a frontend interface, Dockerized services, and includes **training scripts for LoRA-based fine-tuning** of the LLM model. 

---

## Project Structure

### Configuration and Core Files

- `LLM-config.yml` – LLM model configuration.  
- `docker-compose.yml` – Docker Compose setup for all services (database, backend, frontend).  
- `dockerfile` – Docker configuration for the backend application.  
- `main.py` – Main backend application file.  
- `requirements.txt` – Python dependencies for Docker and backend.  
- `schema.sql` – Database schema and initialization scripts.  
- `servers.json` – Database server definitions for pgAdmin.  
- `pllum-lora-model/` – Folder containing LoRA adapter.

### Frontend (`FrontEnd/`)

- `index.html` – HTML template for the user interface.  
- `script.js` – Frontend logic and API interactions.  
- `style.css` – Stylesheet for customizing the UI appearance.  

### Backend Modules (`modules/`)

- `db.py` – Functions for interacting with the database.  
- `models.py` – Data structures used for API requests and responses.  
- `security.py` – User authentication and authorization functions.  

### Training Application (`Training-app/`)

- `QLoRA.py` – Script for training/fine-tuning the LLM model.  
- `requirements.txt` – Python dependencies for training scripts.  
- `train.json` – Dataset for model training.  
- `dockerfile` – Docker configuration for the training environment.  
- `Training-config.yml` – Training-specific configuration parameters.

---

## Requirements for Running

Before running the project, make sure the following requirements are met:

### 0. Docker

This project uses Docker to run the backend, frontend, and PostgreSQL database services. Ensure that **Docker** and **Docker Compose** are installed on your system.

### 1. Base model

The base LLM model must be downloaded and placed in the following folder within the project root:

- **Folder:** `models--CYFRAGOVPL--Llama-PLLuM-8B-chat`
- **Model:**  
  [`models--CYFRAGOVPL--Llama-PLLuM-8B-chat`](https://huggingface.co/CYFRAGOVPL/Llama-PLLuM-8B-chat)
- **Parameters:** 8 billion (8B)
- **Type:** Chat version 
- **Precision:** 16-bit float (bf16)
- **License:** Llama 3.1 Community License Agreement
  
### 2. Environment file `.env`  

Create a `.env` file in the project root directory with the following variables:

```env
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=

PGADMIN_EMAIL=
PGADMIN_PASSWORD=
PGADMIN_DEFAULT_EMAIL=
PGADMIN_DEFAULT_PASSWORD=

JWT_SECRET=
JWT_REFRESH_SECRET=
```

### 3. LoRA adapter

The project also requires a trained **LoRA adapter**:

- **Folder:** `pllum-lora-model/`


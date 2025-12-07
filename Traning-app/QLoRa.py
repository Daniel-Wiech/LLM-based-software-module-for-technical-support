from transformers import (AutoModelForCausalLM,DataCollatorForSeq2Seq, AutoTokenizer, TrainingArguments, pipeline, Trainer, BitsAndBytesConfig)
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, PeftModel,prepare_model_for_kbit_training
from torch.utils.data import DataLoader
import torch
import wandb
import yaml


with open("Training-config.yml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

model_name = config["model_name"]
train_data_path = config["train_data_path"]
output_dir = config["output_lora_dir"]

wandb.init(
    project="pllum-fine-tuning",
    name="pllum-8b-lora",
    config={
        "model_name": model_name,
        "batch_size": config["batch_size"],
        "gradient_accumulation": config["gradient_accumulation"],
        "learning_rate": config["learning_rate"],
        "epochs": config["epochs"],
        "LoRA_r": config["lora_r"]
    })

dataset = load_dataset("json", data_files={"train": train_data_path})["train"]

print("CUDA dostępne:", torch.cuda.is_available())
print("Liczba GPU:", torch.cuda.device_count())
print("Nazwa GPU:", torch.cuda.get_device_name(0))

tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token

def preprocess_data(example):
    prompt = (
        f"Użytkownik: {example['user']}\n"
        f"Asystent: {example['assistant']}"
    )

    tokenized = tokenizer(prompt, max_length=config["tokenizer_max_length"], padding=config["tokenizer_padding"], truncation=config["tokenizer_truncation"])
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized

tokenized_dataset = dataset.map(preprocess_data)
data_collator = DataCollatorForSeq2Seq(
    tokenizer=tokenizer,
    pad_to_multiple_of=config["data_collector_padding"],
    return_tensors=config["data_collector_tensor_type"]
)

bnb_config = BitsAndBytesConfig(
    load_in_4bit=config["load_in_4bit"],
    bnb_4bit_use_double_quant=config["use_double_quant"],
    bnb_4bit_quant_type=config["quant_type"],
    bnb_4bit_compute_dtype=torch.bfloat16
)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    quantization_config=bnb_config
)

model = prepare_model_for_kbit_training(model)

lora_config = LoraConfig(
    r=config["lora_r"],
    lora_alpha=config["lora_alpha"],
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=config["lora_dropout"],
    bias=config["lora_bias"],
    task_type=config["lora_task_type"],
    modules_to_save=["lm_head"]
)

model = get_peft_model(model, lora_config)

training_args = TrainingArguments(
    output_dir=output_dir,
    per_device_train_batch_size=config["batch_size"],
    gradient_accumulation_steps=config["gradient_accumulation"],
    learning_rate=float(config["learning_rate"]),
    num_train_epochs=config["epochs"],
    logging_steps=config["logging_steps"],
    save_strategy=config["save_strategy"],
    save_total_limit=config["save_total_limit"],
    optim=config["optimizer"],
    label_names=["labels"],
    report_to="none",

)

class CustomTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        outputs = model(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            labels=inputs["labels"]
        )
        loss = outputs.loss
        return (loss, outputs) if return_outputs else loss

    def training_step(self, model, inputs, optimizer=None):
        loss = super().training_step(model, inputs)

        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1e9
            reserved = torch.cuda.memory_reserved() / 1e9
        else:
            allocated = reserved = 0.0
        wandb.log({
            "loss": loss.item(),
            "VRAM_allocated_GB": allocated,
            "VRAM_reserved_GB": reserved,
            "learning_rate": self.lr_scheduler.get_last_lr()[0],
        })
        return loss

trainer = CustomTrainer(
    model=model,
    train_dataset=tokenized_dataset,
    args=training_args,
    data_collator=data_collator
)

trainer.train()

trainer.save_model(output_dir)
tokenizer.save_pretrained(output_dir)
print(f"Model zapisany w: {output_dir}")

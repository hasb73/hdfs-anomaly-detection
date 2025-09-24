from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-small")
model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-small")
summ = pipeline("text2text-generation", model=model, tokenizer=tokenizer)

def explain_anomaly(context_text):
    prompt = f"Summarize the root cause and remediation for the following log context:\n\n{context_text}\n\nExplanation:"
    out = summ(prompt, max_length=150, do_sample=False)[0]['generated_text']
    return out

if __name__ == "__main__":
    example = "500 errors spike on /login; logs show repeated 'OutOfMemoryError' in auth service; CPU and memory metrics show increases"
    print(explain_anomaly(example))

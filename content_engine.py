import os, requests

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

def generate_case_study():
    prompt = "Write a technical markdown post titled: 'Deconstructing Cloud Security Policies: Automating ISO 27001 Control Matrices'. Explain the exact manual overhead GRC engineers face and show how deterministic PDF-to-matrix parsing eliminates 40+ engineering hours. Keep it highly technical, including a sample JSON schema output for mapped controls."
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": [{"role": "user", "content": prompt}]
    }
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
    return res.json()["choices"][0]["message"]["content"].strip()

if __name__ == "__main__":
    content = generate_case_study()
    with open("case_study_output.md", "w") as f:
        f.write(content)
    print("Case study generated successfully.")

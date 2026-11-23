from openai import OpenAI

client = OpenAI()

reponse = client.responses.create(
    model="gpt-4.1",
    instructions="Tu es un assistant concis.",
    input="Explique la température d'un LLM en une phrase.",
    temperature=0.7,
    top_p=0.9,
    max_output_tokens=100,
)

print(reponse.output_text)

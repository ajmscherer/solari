import os
from mistralai.client import Mistral

from dotenv import load_dotenv
load_dotenv()

API_KEY = os.environ.get("MISTRAL_API_KEY")
client = Mistral(api_key=API_KEY)

inputs = [
    {"role":"user","content":"Quel jour sommes nous STP?"}
]

response = client.beta.conversations.start(
    agent_id="ag_019d88a34acf7473b61745ca1a938110",
    agent_version=0,
    inputs=inputs,
)

print (inputs[0]['content'])
print(response.outputs[0].content)
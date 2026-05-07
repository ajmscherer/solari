# solari - a simple dashboard app with a Solari board style interface
# Copyright (C) 2024-2026 Alex Scherer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import requests
import os

API_KEY = os.getenv("MISTRAL_API_KEY")

MODEL_ENDPOINT = "https://api.mistral.ai/v1/models"  # Check Mistral's docs for the correct endpoint
CHAT_COMPLETIONS_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"  # Example endpoint

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

def list_available_models()->list|str:
    """List available models from Mistral API."""
    response = requests.get(MODEL_ENDPOINT, headers=headers)
    if response.status_code == 200:
        return response.json()['data']
    else:
        return f"Error: {response.status_code} - {response.text}"

def chat_completion(messages, model="mistral-medium-latest", temperature=0.7):
    """Send a chat completion request to Mistral API."""
    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    response = requests.post(CHAT_COMPLETIONS_ENDPOINT, headers=headers, json=data)
    return response.json()

# Example usage
if __name__ == "__main__":
    # List models (uncomment to test)
    models = list_available_models()
    if isinstance(models, list):
        print("Available models:")
        for model in models:
            print(f"- {model['id']} ")

    # print("Available models:", list_available_models())

    # Chat completion example
    messages = [
        {"role": "user", "content": "Hello! Who are you and what's today's date?"}
    ]
    response = chat_completion(messages)
    print("Assistant:", response["choices"][0]["message"]["content"])


# openai.py 
import openai
import os
import requests
from flask import current_app, jsonify
from config import Config

# Azure OpenAI API settings
azure_api_key = Config.AZURE_API_KEY
azure_api_endpoint = Config.AZURE_API_ENDPOINT
azure_deployment_name = Config.AZURE_DEPLOYMENT_NAME

# Function to call Azure OpenAI's GPT model to classify transactions
def classify_transaction_with_azure(item_name):
    """
    Uses Azure's OpenAI GPT API to classify transaction items (expenses, assets, liabilities, etc.)
    into appropriate accounting categories.
    """
    url = f"{azure_api_key}openai/deployments/{azure_deployment_name}/completions?api-version=2023-10-01-preview"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {azure_api_key}"
    }

    # The prompt we will use for classification
    prompt = f"Classify the following transaction item into an accounting category: {item_name}. The categories are: 'Assets', 'Liabilities', 'Equity', 'Revenue', 'Expenses'. Please return the most appropriate account from the chart of accounts."

    payload = {
        "model": "gpt-4",  # Choose the GPT model available in your Azure OpenAI subscription
        "max_tokens": 50,
        "temperature": 0.2,
        "prompt": prompt
    }

    try:
        # Send request to Azure OpenAI API
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        classification = response.json().get("choices", [{}])[0].get("text", "").strip()

        if classification:
            current_app.logger.debug(f"Azure LLM classified '{item_name}' as: {classification}")
            return classification
        else:
            raise Exception("No classification returned by Azure LLM.")

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error calling Azure LLM API: {str(e)}")
        return "Uncategorized"  # Default classification in case of an error


import json
from typing import Dict

from langchain_openai import ChatOpenAI


def generate_llm_summary(api_key: str, context: Dict) -> str:
    prompt = (
        "You are a data analyst. Summarize the dataset and analysis in 5-8 bullet points, "
        "including key risks or data quality concerns, and any modeling performance. "
        "Be concise and business-friendly.\n\n"
        f"Context:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    )

    try:
        model = ChatOpenAI(
            api_key=api_key,
            model="gpt-4o-mini",
            temperature=0.2,
        )
        response = model.invoke(prompt)
        return response.content.strip()
    except Exception:
        return ""

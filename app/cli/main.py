import json
import os
import typer
import httpx

app = typer.Typer()
problem_app = typer.Typer()
answer_app = typer.Typer()
app.add_typer(problem_app, name="problem")
app.add_typer(answer_app, name="answer")


def get_base_url(url: str | None):
    return url or os.getenv("QNA_BASE_URL", "http://localhost:8000")


def get_headers(api_key: str | None):
    key = api_key or os.getenv("QNA_API_KEY", "")
    return {"Authorization": f"Bearer {key}"}


@app.command()
def search(query: str, mode: str = "hybrid", json_output: bool = typer.Option(False, "--json"), base_url: str | None = None):
    r = httpx.post(f"{get_base_url(base_url)}/api/v1/search", json={"query": query, "mode": mode, "top_k": 10})
    data = r.json()
    if json_output:
        print(json.dumps(data))
    else:
        for row in data.get("results", []):
            print(f"{row['problem_id']} {row['title']} ({row['score']:.3f})")


@problem_app.command("create")
def problem_create(title: str, body_file: str, tags: str = "", base_url: str | None = None, api_key: str | None = None):
    body = open(body_file, "r", encoding="utf-8").read()
    payload = {"title": title, "body_markdown": body, "tags": [t.strip() for t in tags.split(",") if t.strip()]}
    r = httpx.post(f"{get_base_url(base_url)}/api/v1/problems", json=payload, headers=get_headers(api_key))
    print(r.text)


@problem_app.command("show")
def problem_show(problem_id: str, json_output: bool = typer.Option(False, "--json"), base_url: str | None = None):
    r = httpx.get(f"{get_base_url(base_url)}/api/v1/problems/{problem_id}")
    if json_output:
        print(r.text)
    else:
        print(r.json()["title"])


@answer_app.command("create")
def answer_create(problem_id: str, body_file: str, kind: str = "reply", base_url: str | None = None, api_key: str | None = None):
    body = open(body_file, "r", encoding="utf-8").read()
    r = httpx.post(f"{get_base_url(base_url)}/api/v1/problems/{problem_id}/answers", json={"body_markdown": body, "kind": kind}, headers=get_headers(api_key))
    print(r.text)


if __name__ == "__main__":
    app()

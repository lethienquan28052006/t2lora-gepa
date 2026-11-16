import pytest
import respx

from t2lgepa.client import AdapterNotLoaded, GenerationError, VLLMClient

URL = "http://localhost:8000"
BASE = "google/gemma-2-2b-it"
CHAT_RESP = {
    "choices": [{"message": {"content": "#### 18"}, "finish_reason": "stop"}],
    "usage": {"completion_tokens": 5},
}


@pytest.fixture
def respx_mock():
    with respx.mock(assert_all_called=False) as mock:
        yield mock


def test_unknown_adapter_fails_loudly(respx_mock):
    respx_mock.get(f"{URL}/v1/models").respond(json={"data": [{"id": BASE}]})
    with pytest.raises(AdapterNotLoaded):
        VLLMClient(URL, BASE, adapters=["t2l_gsm8k"]).assert_ready()


def test_ready_when_all_names_present(respx_mock):
    respx_mock.get(f"{URL}/v1/models").respond(
        json={"data": [{"id": BASE}, {"id": "t2l_gsm8k"}]}
    )
    VLLMClient(URL, BASE, adapters=["t2l_gsm8k"]).assert_ready()


def test_generate_keeps_requested_model(respx_mock):
    route = respx_mock.post(f"{URL}/v1/chat/completions").respond(json=CHAT_RESP)
    out = VLLMClient(URL, BASE, adapters=["t2l_gsm8k"]).generate(["q"], model="t2l_gsm8k")
    assert route.calls[0].request.content.count(b"t2l_gsm8k") == 1
    assert out[0].text == "#### 18"
    assert out[0].n_tokens == 5


def test_http_error_raises_not_empty_string(respx_mock):
    respx_mock.post(f"{URL}/v1/chat/completions").respond(status_code=500)
    with pytest.raises(GenerationError):
        VLLMClient(URL, BASE, adapters=[]).generate(["q"], model=BASE)


def test_requested_model_must_be_base_or_known_adapter(respx_mock):
    with pytest.raises(AdapterNotLoaded):
        VLLMClient(URL, BASE, adapters=["t2l_gsm8k"]).generate(["q"], model="typo_adapter")


def test_generate_preserves_input_order_with_concurrency(respx_mock):
    import json

    import httpx

    def handler(request):
        prompt = json.loads(request.content)["messages"][0]["content"]
        text = "#### 18" if prompt == "a" else "#### 7"
        return httpx.Response(200, json={
            "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
            "usage": {"completion_tokens": 5},
        })

    respx_mock.post(f"{URL}/v1/chat/completions").mock(side_effect=handler)
    out = VLLMClient(URL, BASE, adapters=[]).generate(["a", "b"] * 5, model=BASE)
    assert [g.text for g in out] == ["#### 18", "#### 7"] * 5


def test_api_key_is_sent_as_bearer(respx_mock):
    route = respx_mock.post(f"{URL}/v1/chat/completions").respond(json=CHAT_RESP)
    client = VLLMClient(URL, "deepseek-v4.1-flash", adapters=[], api_key="sk-test")
    client.generate(["q"], model="deepseek-v4.1-flash")
    assert route.calls[0].request.headers["authorization"] == "Bearer sk-test"


def test_external_model_is_accepted_when_served_by_the_endpoint(respx_mock):
    respx_mock.get(f"{URL}/v1/models").respond(json={"data": [{"id": "deepseek-v4.1-flash"}]})
    VLLMClient(URL, "deepseek-v4.1-flash", adapters=[]).assert_ready()


def test_base_url_already_ending_in_v1_is_not_doubled(respx_mock):
    route = respx_mock.get("https://api.example/v1/models").respond(
        json={"data": [{"id": "deepseek-v4.1-flash"}]})
    VLLMClient("https://api.example/v1", "deepseek-v4.1-flash", adapters=[]).assert_ready()
    assert route.called

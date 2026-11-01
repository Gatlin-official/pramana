# Eval set review checklist (random 30%)

Questions were drafted by a local LLM. Check each row below, then edit `eval/questions.jsonl`:
fix the `question` text if needed, set `"reviewed": true`, or set `"drop": true` to exclude it.
Gold spans are char offsets into the document text; if the evidence is wrong, drop the row rather
than editing offsets by hand. Re-run `make eval` afterwards (results are cached per question set hash).

## q005 · single

**Q:** What error response is sent when a client sends extra form fields that are not allowed?

**Reference answer:** The error response indicates that extra inputs are not permitted.

Evidence from `tutorial/request-form-models.md` (chars 1749-2062):

> They will receive an error response telling them that the field `extra` is not allowed:
> 
> ```json
> {
>     "detail": [
>         {
>             "type": "extra_forbidden",
>             "loc": ["body", "extra"],
>             "msg": "Extra inputs are not permitted",
>             "input": "Mr. Poopybutthole"
>         }
>     ]
> }

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q007 · single

**Q:** How can I restrict FastAPI from accepting extra headers in a request?

**Reference answer:** You can use Pydantic's model configuration to forbid any extra fields.

Evidence from `tutorial/header-param-models.md` (chars 1171-1318):

> You can use Pydantic's model configuration to `forbid` any `extra` fields:
> 
> {* ../../docs_src/header_param_models/tutorial002_an_py310.py hl[10] *}

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q008 · single

**Q:** How does FastAPI handle data retrieved from the Request object directly?

**Reference answer:** FastAPI does not validate, convert, or document data retrieved from the Request object directly.

Evidence from `advanced/using-request-directly.md` (chars 716-931):

> It would also mean that if you get data from the `Request` object directly (for example, read the body) it won't be validated, converted or documented (with OpenAPI, for the automatic API user interface) by FastAPI.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q009 · single

**Q:** How can I add dependencies to all path operations in a FastAPI application?

**Reference answer:** You can add dependencies to the `FastAPI` application, which applies them to all path operations.

Evidence from `tutorial/dependencies/global-dependencies.md` (chars 141-402):

> Similar to the way you can [add `dependencies` to the *path operation decorators*](dependencies-in-path-operation-decorators.md), you can add them to the `FastAPI` application.
> 
> In that case, they will be applied to all the *path operations* in the application:

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q010 · single

**Q:** How can I stream Server-Sent Events (SSE) in FastAPI?

**Reference answer:** You can stream Server-Sent Events (SSE) in FastAPI by using `yield` in your path operation function and setting `response_class=EventSourceResponse`.

Evidence from `reference/sse.md` (chars 68-195):

> To stream Server-Sent Events (SSE), use `yield` in your *path operation function* and set `response_class=EventSourceResponse`.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q012 · single

**Q:** Can I use Starlette's Response in FastAPI?

**Reference answer:** Yes, you can use Starlette's Response in FastAPI.

Evidence from `advanced/response-cookies.md` (chars 1661-1961):

> You could also use `from starlette.responses import Response` or `from starlette.responses import JSONResponse`.
> 
> **FastAPI** provides the same `starlette.responses` as `fastapi.responses` just as a convenience for you, the developer. But most of the available responses come directly from Starlette.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q013 · single

**Q:** What is the execution order of middlewares when adding multiple ones with `app.add_middleware()`?

**Reference answer:** The last middleware added is executed first on the request path.

Evidence from `tutorial/middleware.md` (chars 2944-3255):

> When you add multiple middlewares using either `@app.middleware()` decorator or `app.add_middleware()` method, each new middleware wraps the application, forming a stack. The last middleware added is the *outermost*, and the first is the *innermost*.
> 
> On the request path, the *outermost* middleware runs first.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q016 · single

**Q:** How does FastAPI handle the sub-application's documentation UI path when it is mounted?

**Reference answer:** FastAPI uses the `root_path` mechanism from the ASGI specification to communicate the mount path for the sub-application, allowing the sub-application to use the correct path prefix for its documentation UI.

Evidence from `advanced/sub-applications.md` (chars 2424-2652):

> FastAPI will take care of communicating the mount path for the sub-application using a mechanism from the ASGI specification called a `root_path`.
> 
> That way, the sub-application will know to use that path prefix for the docs UI.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q020 · single

**Q:** What is the benefit of using a Response Model over returning a JSONResponse directly in FastAPI?

**Reference answer:** Using a Response Model provides better performance as it serializes data using Pydantic in Rust, compared to returning a JSONResponse directly.

Evidence from `advanced/response-directly.md` (chars 594-798):

> You will normally have much better performance using a [Response Model](../tutorial/response-model.md) than returning a `JSONResponse` directly, as that way it serializes the data using Pydantic, in Rust.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q028 · single

**Q:** Why was FastAPI created instead of using existing frameworks?

**Reference answer:** FastAPI was created because existing frameworks, plug-ins, and tools couldn't provide all the required features together.

Evidence from `history-design-future.md` (chars 929-1220):

> I have been avoiding the creation of a new framework for several years. First I tried to solve all the features covered by **FastAPI** using many different frameworks, plug-ins, and tools.
> 
> But at some point, there was no other option than creating something that provided all these features

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q029 · single

**Q:** How do you import the CORSMiddleware in FastAPI?

**Reference answer:** You import CORSMiddleware using `from fastapi.middleware.cors import CORSMiddleware`.

Evidence from `reference/middleware.md` (chars 242-338):

> It can be imported from `fastapi`:
> 
> ```python
> from fastapi.middleware.cors import CORSMiddleware

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q031 · single

**Q:** How can I ensure the lifespan events run in my FastAPI tests?

**Reference answer:** Use the `TestClient` with a `with` statement to run lifespan events in tests.

Evidence from `advanced/testing-events.md` (chars 101-201):

> When you need `lifespan` to run in your tests, you can use the `TestClient` with a `with` statement:

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q042 · single

**Q:** What happens to the exit code of a dependency with `yield` when using `StreamingResponse` in FastAPI versions before 0.118.0?

**Reference answer:** The exit code of a dependency with `yield` is executed right before sending the response when using `StreamingResponse` in FastAPI versions before 0.118.0.

Evidence from `advanced/advanced-dependencies.md` (chars 3976-4420):

> Before FastAPI 0.118.0, if you used a dependency with `yield`, it would run the exit code after the *path operation function* returned but right before sending the response.
> 
> The intention was to avoid holding resources for longer than necessary, waiting for the response to travel through the network.
> 
> This change also meant that if you returned a `StreamingResponse`, the exit code of the dependency with `yield` would have been already run.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q047 · single

**Q:** What is the purpose of the interactive docs provided by FastAPI?

**Reference answer:** The interactive docs provided by FastAPI are used by the frontend team, third-party applications, and yourself to debug, check, and test the same application.

Evidence from `tutorial/security/first-steps.md` (chars 2364-2570):

> It can be used by the frontend team (that can also be yourself).
> 
> It can be used by third party applications and systems.
> 
> And it can also be used by yourself, to debug, check and test the same application.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q051 · single

**Q:** How can you import the WebSocket class in FastAPI?

**Reference answer:** You can import the WebSocket class from `fastapi`.

Evidence from `reference/websockets.md` (chars 269-385):

> It is provided directly by Starlette, but you can import it from `fastapi`:
> 
> ```python
> from fastapi import WebSocket

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q054 · single

**Q:** How can you avoid calling an external authentication provider during tests?

**Reference answer:** You can override the dependency that calls the external provider with a custom dependency that returns a mock user during tests.

Evidence from `advanced/testing-dependencies.md` (chars 255-570):

> You don't want the original dependency to run (nor any of the sub-dependencies it might have).
> 
> Instead, you want to provide a different dependency that will be used only during tests (possibly only some specific tests), and will provide a value that can be used where the value of the original dependency was used.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q055 · single

**Q:** How does FastAPI handle cookie parameters defined in a Pydantic model?

**Reference answer:** FastAPI extracts the data for each field from the cookies received in the request and provides the defined Pydantic model.

Evidence from `tutorial/cookie-param-models.md` (chars 728-874):

> **FastAPI** will **extract** the data for **each field** from the **cookies** received in the request and give you the Pydantic model you defined.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q056 · single

**Q:** How does FastAPI automatically configure OpenTelemetry providers and exporters?

**Reference answer:** FastAPI automatically uses configured providers and adds an exporter for each enabled provider when an OTLP endpoint is set in the environment.

Evidence from `advanced/opentelemetry.md` (chars 3627-3944):

> Configure the library before the app starts, and FastAPI uses those providers automatically.
> 
> By default, FastAPI uses configured providers without adding exporters. When automatic setup is enabled and an OTLP endpoint is set in the environment, FastAPI adds an exporter for that destination to each enabled provider.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q065 · single

**Q:** How does FastAPI handle shared query parameters between multiple models?

**Reference answer:** FastAPI validates shared query parameters independently for each model, and OpenAPI lists them once with the same type and constraints.

Evidence from `tutorial/query-param-models.md` (chars 2624-2940):

> If models share a parameter name or alias, each model validates that request parameter independently. Use distinct names or aliases for independent values. OpenAPI lists a shared parameter once, as it does for parameters shared with dependencies, so shared declarations should describe the same type and constraints.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q069 · multi

**Q:** What versions of FastAPI and Pydantic are required to use `pydantic.v1` and why is this important?

**Reference answer:** FastAPI 0.128.0 and later versions no longer support `pydantic.v1`, requiring Pydantic v2, as the Pydantic team stopped supporting Pydantic v1 in Python 3.14 and above.

Evidence from `how-to/migrate-from-pydantic-v1-to-pydantic-v2.md` (chars 526-639):

> FastAPI 0.128.0 dropped support for `pydantic.v1` as well, so the latest versions of FastAPI require Pydantic v2.

Evidence from `how-to/migrate-from-pydantic-v1-to-pydantic-v2.md` (chars 2922-3014):

> In current versions of FastAPI, using a `pydantic.v1` model in your app will raise an error.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q071 · multi

**Q:** How can I use a custom response class with FastAPI while still having the response documented in OpenAPI?

**Reference answer:** Use the `response_class` parameter to document the media type in OpenAPI and return a `Response` object to customize the response.

Evidence from `advanced/custom-response.md` (chars 3604-3929):

> If you want to override the response from inside of the function but at the same time document the "media type" in OpenAPI, you can use the `response_class` parameter AND return a `Response` object.
> 
> The `response_class` will then be used only to document the OpenAPI *path operation*, but your `Response` will be used as is.

Evidence from `advanced/custom-response.md` (chars 9516-9671):

> You could create a `CustomORJSONResponse`. The main thing you have to do is create a `Response.render(content)` method that returns the content as `bytes`:

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q073 · multi

**Q:** How can I specify a custom HTTP status code in FastAPI and what are the common ranges for different types of responses?

**Reference answer:** You can specify a custom HTTP status code in FastAPI using the `status_code` parameter in path operations, and common ranges include 200-299 for successful responses, 400-499 for client errors, and 500-599 for server errors.

Evidence from `tutorial/response-status-code.md` (chars 1332-1514):

> In HTTP, you send a numeric status code of 3 digits as part of the response.
> 
> These status codes have an associated name to help recognize them, but the important part is the number.

Evidence from `tutorial/response-status-code.md` (chars 50-226):

> The same way you can specify a response model, you can also declare the HTTP status code used for the response with the parameter `status_code` in any of the *path operations*:

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q074 · multi

**Q:** How can I show multiple examples in the docs UI using FastAPI?

**Reference answer:** Use the `openapi_examples` parameter with a `dict` of multiple examples to show them in the docs UI.

Evidence from `tutorial/schema-extra-example.md` (chars 3464-3644):

> The shape of this OpenAPI-specific field `examples` is a `dict` with **multiple examples** (instead of a `list`), each with extra information that will be added to **OpenAPI** too.

Evidence from `tutorial/schema-extra-example.md` (chars 2500-2722):

> You can of course also pass multiple `examples`:
> 
> {* ../../docs_src/schema_extra_example/tutorial004_an_py310.py hl[23:38] *}
> 
> When you do this, the examples will be part of the internal **JSON Schema** for that body data.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q075 · multi

**Q:** How does FastAPI handle the execution of code before and after the application starts handling requests, and what is the role of an async context manager in this process?

**Reference answer:** FastAPI uses an async context manager to execute code before the application starts by running the code before the `yield`, and after the application finishes by running the code after the `yield`.

Evidence from `advanced/events.md` (chars 3257-3449):

> The first part of the function, before the `yield`, will be executed **before** the application starts.
> 
> And the part after the `yield` will be executed **after** the application has finished.

Evidence from `advanced/events.md` (chars 4095-4349):

> When you create a context manager or an async context manager like above, what it does is that, before entering the `with` block, it will execute the code before the `yield`, and after exiting the `with` block, it will execute the code after the `yield`.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q081 · multi

**Q:** How do I run the code examples and install the AI agent skill?

**Reference answer:** Install the AI agent skill using `uvx library-skills` and run examples with `uv run fastapi dev`.

Evidence from `tutorial/index.md` (chars 6320-6476):

> After installing FastAPI in your project, you can install the skill with <a href="https://library-skills.io">Library Skills</a>:
> 
> ```bash
> uvx library-skills

Evidence from `tutorial/index.md` (chars 543-727):

> To run any of the examples, copy the code to a file `main.py`, and start `fastapi dev` with `uv run`:
> 
> <div class="termy">
> 
> ```console
> $ <font color="#4E9A06">uv run fastapi</font> dev

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q084 · multi

**Q:** How do the `contact` and `license_info` fields differ in their required fields and structure according to the documentation?

**Reference answer:** The `contact` field requires `name`, `url`, and `email` fields, while the `license_info` field requires `name` and either `identifier` or `url` but not both.

Evidence from `tutorial/metadata.md` (chars 1413-1547):

> The email address of the contact person/organization. MUST be in the format of an email address.</td></tr></tbody></table></details> |

Evidence from `tutorial/metadata.md` (chars 864-1547):

> The contact information for the exposed API. It can contain several fields. <details><summary><code>contact</code> fields</summary><table><thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>name</code></td><td><code>str</code></td><td>The identifying name of the contact person/organization.</td></tr><tr><td><code>url</code></td><td><code>str</code></td><td>The URL pointing to the contact information. MUST be in the format of a URL.</td></tr><tr><td><code>email</code></td><td><code>str</code></td><td>The email address of the contact person/organization. MUST be in the format of an email address.</td></tr></tbody></table></details> |

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q091 · paraphrase

**Q:** Can I send back different kinds of information from a function in FastAPI?

**Reference answer:** Yes, you can return various data types such as dictionaries, lists, strings, integers, and Pydantic models from a path operation function in FastAPI.

Evidence from `tutorial/first-steps.md` (chars 12537-12789):

> You can return a `dict`, `list`, singular values as `str`, `int`, etc.
> 
> You can also return Pydantic models (you'll see more about that later).
> 
> There are many other objects and models that will be automatically converted to JSON (including ORMs, etc).

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q093 · paraphrase

**Q:** When you're setting up a FastAPI app to work on a server, why is it better to have more than one copy of the app running at the same time?

**Reference answer:** Replication of processes helps take advantage of multiple cores and handle more requests.

Evidence from `deployment/server-workers.md` (chars 484-656):

> When deploying applications you will probably want to have some **replication of processes** to take advantage of **multiple cores** and to be able to handle more requests.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q094 · paraphrase

**Q:** What happens if I turn on the option to allow cookies in FastAPI?

**Reference answer:** If `allow_credentials` is set to `True`, `allow_origins`, `allow_methods`, and `allow_headers` cannot be set to `['*']` and must be explicitly specified.

Evidence from `tutorial/cors.md` (chars 3798-4057):

> None of `allow_origins`, `allow_methods` and `allow_headers` can be set to `['*']` if `allow_credentials` is set to `True`. All of them must be [explicitly specified](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#credentialed_requests_and_wildcards).

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q097 · paraphrase

**Q:** Why is using a secure connection important for apps built with FastAPI, according to the guide?

**Reference answer:** HTTPS is very important and quite critical in most cases.

Evidence from `deployment/https.md` (chars 13799-14001):

> Having **HTTPS** is very important, and quite **critical** in most cases. Most of the effort you as a developer have to put around HTTPS is just about **understanding these concepts** and how they work.

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q105 · paraphrase

**Q:** How can I make a web app that has two different pages? One should show a greeting, and the other should show information about a specific item using a number.

**Reference answer:** You create a `main.py` file with the FastAPI app and two endpoints using `@app.get`.

Evidence from `index.md` (chars 11116-11386):

> Create a file `main.py` with:
> 
> ```Python
> from fastapi import FastAPI
> 
> app = FastAPI()
> 
> 
> @app.get("/")
> def read_root():
>     return {"Hello": "World"}
> 
> 
> @app.get("/items/{item_id}")
> def read_item(item_id: int, q: str | None = None):
>     return {"item_id": item_id, "q": q}

- [ ] Question is clear and self-contained
- [ ] Evidence actually answers it
- [ ] Reference answer is correct

## q106 · unanswerable

**Q:** How do I deploy a FastAPI app to AWS Lambda using Mangum?

- [ ] FastAPI docs truly do not answer this

## q109 · unanswerable

**Q:** How do I expose Prometheus metrics from a FastAPI application?

- [ ] FastAPI docs truly do not answer this

## q110 · unanswerable

**Q:** Can I define gRPC services alongside my REST endpoints in FastAPI?

- [ ] FastAPI docs truly do not answer this

## q116 · unanswerable

**Q:** How do I deploy FastAPI as an Azure Functions app?

- [ ] FastAPI docs truly do not answer this

## q118 · unanswerable

**Q:** How do I implement GraphQL subscriptions in FastAPI?

- [ ] FastAPI docs truly do not answer this

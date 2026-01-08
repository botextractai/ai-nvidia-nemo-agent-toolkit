# NVIDIA's NeMo Agent Toolkit - one framework to orchestrate, configure, and observe diverse AI agents

NVIDIA's open-source NeMo Agent Toolkit (NAT) is a powerful "master" agent framework designed to orchestrate complex Artificial Intelligence (AI) systems without locking you into a single provider, model, or agent style. Its key strength is integration: NAT can combine multiple providers (including local hosting, for example trough Ollama), Large Language Models (LLMs), tools, and agents (including those built in other agent frameworks) into a single workflow. A clear, declarative YAML configuration file lets you define models, agent interactions, and tool wiring, making it easy to swap components, reuse agents, and scale systems with minimal refactoring. NAT is built with real-world deployment in mind, offering strong support for Application Programming Interface (API) and web front-end integration, as well as built-in observability and tracing, so that you can see what agents are doing and why.

NAT works with agents built in custom Python code, LangChain / LangGraph, LlamaIndex, CrewAI, or any other agentic framework. NeMo stands for "neutral modules".

NAT is configuration-driven via a YAML file. This configuration-driven approach means that you can integrate LLMs from multiple providers (including locally hosted models), or swap tools by changing a few lines with no code refactoring required. The YAML configuration file first declares shared providers (such as LLMs and embedders), "functions" that define callable tools (including agents exposed as tools), and other optional components, such as memory and retrievers. A "workflow" section then defines the execution flow, instantiating one or more agents that reference these providers, functions, and other components.

This example uses a dataset of global temperature records from the United States National Oceanic and Atmospheric Administration (NOAA). The dataset includes 75 years of data (1950-2025) for 10 countries worldwide with weather station measurements and annual temperature averages in degrees Celsius.

This example contains 2 self-contained parts. The first part `simple_workflow` demonstrates the most basic workflow, the API server, and the NAT web user interface. The second part `climate_analyzer` demonstrate multiple LLMs, tools, agent integration, traceability with Arize Phoenix, and evaluation.

## Setup

You first need to install all required Python dependencies, including the `climate_analyzer` component and its entry point, using this command:

```bash
pip install -e .
```

### Required API key for this example

You need an OpenAI API key for this example. [Get your OpenAI API key here](https://platform.openai.com/login). Insert the OpenAI API key into the `.env.example` file and then rename this file to just `.env` (remove the ".example" ending).

You need to activate your environment variables from the `.env` file (in this example just the OpenAI API key) with one of the following two options, depending on your operating system. Please note that you will have to repeat this for every session, as environment variables set in this way are not permanent. Alternatively, you can also prefix all commands with `python env_setup.py`, for example: `python env_setup.py <YOUR_COMMAND_GOES_HERE>`.

#### If you use Linux or Apple macOS: Export variables for shell

```bash
source <(python env_setup.py --export)
```

#### If you use Microsoft Windows: Export variables for PowerShell

```bash
python env_setup.py --export | ForEach-Object { Invoke-Expression $_ }
```

## PART 1: simple_workflow

This part shows the most basic implementation of NAT. The workflow uses the type `chat_completion`, which requires a chat-style LLM to reply to a conversation. It uses the bare LLM without any tools.

### Running from command line

You can call the `simple_workflow` directly from command line:

```bash
nat run --config_file simple_workflow/config.yml --input "What is the difference between weather and climate?"
```

### Application Programming Interface (API)

NAT can automatically create an Application Programming Interface (API) when you run this command to start an API server:

```bash
nat serve --config_file simple_workflow/config.yml
```

Once you have started the API server and kept it running (in a separate terminal session), you can test it with this Python script. It uses the API to ask the question "How do ocean currents affect climate?":

```bash
python simple_workflow/check_local_api.py
```

NAT also automatically creates the API documentation, which you can access in your browser with `http://localhost:8000/docs`.

### Web user interface

The NAT web user interface requires the `NeMo-Agent-Toolkit-UI`. This example already includes the toolkit, but you still need to run the `npm install` command in the `NeMo-Agent-Toolkit-UI` folder as described below to install the JavaScript dependencies.

If you want to replace the existing toolkit version with a newer one, then you can just delete the existing `NeMo-Agent-Toolkit-UI` folder and clone a new one from GitHub with this command:

```bash
git clone https://github.com/NVIDIA/NeMo-Agent-Toolkit-UI.git
```

If you don't have "Node.js" already installed on your system, then you must install "Node.js", which includes the Node Package Manager (NPM). Once you have installed "Node.js", you can install the JavaScript dependencies with these two commands:

```bash
cd NeMo-Agent-Toolkit-UI
npm install
```

When you have the API server running (as described in the previous step), you can use the NAT web user interface (or alternatively any other LLM web user interface like Gradio, Streamlit etc.). Use this example Python script to start the NAT web user interface from command line:

```bash
python simple_workflow/web_ui.py
```

When you have both the API server and the NAT web user interface running (both in separate terminal sessions), you can access the NAT web user interface in your browser with `http://localhost:3000`.

## PART 2: climate_analyzer

This part shows the use of 6 Python tools and 1 LangGraph agent in NAT. The LangGraph agent is an example that shows how to integrate existing agents from other agent frameworks. NAT provides direct support for Google's Agent Development Kit (ADK), Agno, CrewAI, LangChain / LangGraph, LlamaIndex, and other frameworks (e.g., Semantic Kernel, custom agents).

The `climate_analyzer` workflow follows the Reasoning and Acting (ReAct) agent pattern.

This part also adds observability using OpenTelemetry tracing with a local Arize Phoenix server. Arize Phoenix captures every step of your agent's reasoning process - which tools it calls, what data flows between them, and how long each operation takes. This visibility lets you identify problems and make data-driven improvements.

To enable Arize Phoenix tracing, you just add a telemetry section to your YAML configuration file. This tells NAT where to send trace data.

Finally, this part also shows how to evaluate your agent using evaluation datasets with ground truth answers and how to run systematic tests.

You must have your local Arize Phoenix server running in a separate terminal session. You can start your local Arize Phoenix server with this command:

```bash
phoenix serve
```

Once that your Arize Phoenix server is running, you can access the Arize Phoenix web user interface (and later see the results) in your browser with `http://localhost:6006`.

![alt text](https://github.com/user-attachments/assets/09848b5b-3b11-487a-bba7-2a9c289ce903 "Arize Phoenix")

### Tools

The 6 Python tools of the `climate_analyzer` are designed to:

1. `list_countries`: List all available countries in the dataset
2. `calculate_statistics`: Calculate temperature statistics globally or for a specific country
3. `filter_by_country`: Get information about climate data for a specific country
4. `find_extreme_years`: Find the warmest or coldest years in the dataset
5. `create_visualization`: Create visualizations including automatic top 5 countries by warming trend
6. `station_statistics`: Get statistics on climate stations used in the data

The 1 LangGraph agent is:

1. `calculator_agent`: A LangGraph calculator agent that can handle complex mathematical operations

The key to integrating external agents like the LangGraph `calculator_agent` is the NAT "LLM Lifting" pattern. Instead of hardcoding the LLM inside the calculator agent, you "lift" it to the NAT YAML configuration file. This allows you to use different LLMs for each agent, and/or different agent settings (in this example for the number of maximum tokens). Please note that NAT can only define or override the agent LLM via the YAML configuration file, if the agent is designed with an injection point for the model.

You can test the correct use of the tools with these 7 example questions.

#### Question 1: Global trends (low complexity)

Expected tool: `calculate_statistics`

```bash
nat run --config_file climate_analyzer/src/climate_analyzer/configs/config.yml --input "What is the global temperature trend per decade?"
```

#### Question 2: Country analysis (moderate complexity)

Expected tools: `filter_by_country`, `calculate_statistics`

```bash
nat run --config_file climate_analyzer/src/climate_analyzer/configs/config.yml --input "Tell me about France's climate data. How many stations does it have and what's the temperature trend?"
```

#### Question 3: Visualizations (moderate complexity)

Expected tool: `create_visualization`. This will create a graph file in Portable Network Graphics (PNG) format.

```bash
nat run --config_file climate_analyzer/src/climate_analyzer/configs/config.yml --input "Create a visualization showing which countries have the highest warming trends."
```

#### Question 4: Multi-step analysis (high complexity)

Expected tools: `calculate_statistics` (2x), `calculator_agent`, `create_visualization`. This will create a graph file in PNG format.

```bash
nat run --config_file climate_analyzer/src/climate_analyzer/configs/config.yml --input "Compare the temperature trends of Canada and Brazil. Which one is warming faster? Also create a visualization of global trends."
```

#### Question 5: Use the LangGraph agent for calculations with all data in the prompt (low complexity)

Expected tool: `calculator_agent`

```bash
nat run --config_file climate_analyzer/src/climate_analyzer/configs/config.yml --input "A country's emissions were 1200 Mt in 2016. They reduced emissions by 2.5% annually until 2021, then accelerated reductions to 4% annually. What are the emissions in 2026?"
```

#### Question 6: Test the LangGraph agent (tool) with country trend and future projection (medium complexity)

Expected tools: `calculate_statistics`, `calculator_agent`

```bash
nat run --config_file climate_analyzer/src/climate_analyzer/configs/config.yml --input "Get the temperature statistics for India and find its trend per decade. If India's temperature continues to change at this rate, what will the temperature be in 2050?"
```

#### Question 7: Test the LangGraph agent (tool) with county average vs global average (medium complexity)

Expected tools: `calculatre_statistics` (2x), `calculator_agent`

```bash
nat run --config_file climate_analyzer/src/climate_analyzer/configs/config.yml --input "What was Mexico's average temperature 1990-2000 vs global?"
```

### Evaluation

For evaluation, you need to add an `eval` section to your YAML configuration file.

This example already contains a JSON evaluation dataset called `simple_eval.json` in the `climate_analyzer/data` folder. It contains just 1 record.

You run the evaluation with this command:

```bash
nat eval --config_file climate_analyzer/src/climate_analyzer/configs/config.yml
```

The evaluation process goes through these steps:

1. NAT loads your test dataset
2. For each test case, it runs your agent with the question
3. It captures the agent's reasoning steps and final answer
4. It sends both the agent's answer and reference answer to the LLM judge
5. It collects scores and saves detailed results to 2 JSON files in the `evaluation_results` folder. The first file is called `answer_accuracy_output.json` and contains detailed results with evaluation score(s). The second file is called `eval_summary.json` and contains high-level metrics.

The `evaluation_results` folder also contains a Python script called `show_results.py`, which shows the `answer_accuracy_output.json` in a form that is easier to read. You can run the Python script with this command:

```bash
python evaluation_results/show_results.py
```

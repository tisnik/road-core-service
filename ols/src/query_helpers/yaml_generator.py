"""Class responsible for generating YAML responses to user requests."""

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from ols.src import constants
from ols.src.llms.llm_loader import LLMLoader
from ols.utils import config
from ols.utils.logger import Logger


class YamlGenerator:
    """This class is responsible for generating YAML responses to user requests."""

    def __init__(self) -> None:
        """Initializes the `YamlGenerator` instance."""
        self.logger = Logger("yaml_generator").logger

    def generate_yaml(
        self, conversation_id: str, query: str, history: str = None, **kwargs
    ) -> str:
        """Generates YAML response to a user request.

        Args:
          conversation_id: The identifier for the conversation or task context.
          query: The user request.
          history: The history of the conversation (if available).
          **kwargs: Additional keyword arguments for customization.

        Returns:
            The generated YAML response.
        """
        model = config.ols_config.validator_model
        provider = config.ols_config.validator_provider

        verbose = kwargs.get("verbose", "").lower() == "true"
        settings_string = f"conversation: {conversation_id}, query: {query}, provider: {provider}, model: {model}, verbose: {verbose}"
        self.logger.info(f"{conversation_id} call settings: {settings_string}")
        self.logger.info(f"{conversation_id} using model: {model}")

        bare_llm = LLMLoader(provider, model).llm

        if history:
            prompt_instructions = PromptTemplate.from_template(
                constants.YAML_GENERATOR_WITH_HISTORY_PROMPT_TEMPLATE
            )
            task_query = prompt_instructions.format(query=query, history=history)
        else:
            prompt_instructions = PromptTemplate.from_template(
                constants.YAML_GENERATOR_PROMPT_TEMPLATE
            )
            task_query = prompt_instructions.format(query=query)

        self.logger.info(f"{conversation_id} task query: {task_query}")
        llm_chain = LLMChain(llm=bare_llm, verbose=verbose, prompt=prompt_instructions)
        response = llm_chain(inputs={"query": query, "history": history})
        self.logger.info(f"{conversation_id} response:\n{response['text']}")
        return response["text"]
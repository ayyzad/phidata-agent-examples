from typing import Optional, Iterator
from phi.tools import Toolkit
from phi.workflow import Workflow, RunResponse, RunEvent
from phi.agent import Agent
from phi.tools.duckduckgo import DuckDuckGo
from pydantic import BaseModel, Field
import json
from phi.utils.log import logger
from phi.storage.workflow.sqlite import SqlWorkflowStorage
from pathlib import Path

class NewsArticle(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(..., description="Summary of the article if available.")

class SearchResults(BaseModel):
    articles: list[NewsArticle]

class ContentGenerationWorkflow(Workflow):
    searcher: Agent = Agent(
        tools=[DuckDuckGo()],
        instructions=["Given a topic, search for 20 articles and return the 5 most relevant articles."],
        response_model=SearchResults,
    )
    
    writer: Agent = Agent(
        instructions=[
            "You will be provided with a topic and a list of top articles on that topic.",
            "Carefully read each article and generate a New York Times worthy blog post on that topic.",
            "Break the blog post into sections and provide key takeaways at the end.",
            "Make sure the title is catchy and engaging.",
            "Always provide sources, do not make up information or sources.",
        ],
    )

    def save_session_state(self):
        """Custom method to save session state."""
        # Create tmp directory if it doesn't exist
        Path("tmp").mkdir(exist_ok=True, parents=True)
        with open(f"tmp/session_state_{self.session_id}.json", "w") as f:
            json.dump(self.session_state, f)

    def run(self, topic: str, use_cache: bool = True) -> Iterator[RunResponse]:
        """Generate a blog post on a given topic."""
        logger.info(f"Generating a blog post on: {topic}")

        # Use cached blog post if available
        if use_cache and "blog_posts" in self.session_state:
            logger.info("Checking if cached blog post exists")
            for cached_blog_post in self.session_state["blog_posts"]:
                if cached_blog_post["topic"] == topic:
                    logger.info("Found cached blog post")
                    logger.debug(f"Cached content: {cached_blog_post['blog_post'][:200]}...")  # Log first 200 chars
                    yield RunResponse(
                        run_id=self.run_id,
                        event=RunEvent.workflow_completed,
                        content=cached_blog_post["blog_post"],
                    )
                    return

        # Step 1: Search the web for articles on the topic
        num_tries = 0
        search_results: Optional[SearchResults] = None
        while search_results is None and num_tries < 3:
            try:
                num_tries += 1
                searcher_response: RunResponse = self.searcher.run(topic)
                if (
                    searcher_response
                    and searcher_response.content
                    and isinstance(searcher_response.content, SearchResults)
                ):
                    logger.info(f"Searcher found {len(searcher_response.content.articles)} articles.")
                    search_results = searcher_response.content
                else:
                    logger.warning("Searcher response invalid, trying again...")
            except Exception as e:
                logger.warning(f"Error running searcher: {e}")

        # If no search_results are found for the topic, end the process
        if search_results is None or len(search_results.articles) == 0:
            error_msg = f"Sorry, could not find any articles on the topic: {topic}"
            logger.error(error_msg)
            yield RunResponse(
                run_id=self.run_id,
                event=RunEvent.workflow_completed,
                content=error_msg,
            )
            return

        # Step 2: Write a blog post
        logger.info("Writing blog post")
        writer_input = {
            "topic": topic,
            "articles": [v.model_dump() for v in search_results.articles],
        }
        
        # Log the writer input
        logger.debug(f"Writer input: {json.dumps(writer_input, indent=4)}")

        # Simplified writer execution - yield directly from writer.run
        writer_responses = list(self.writer.run(json.dumps(writer_input, indent=4), stream=True))
        
        # Log the writer responses
        for response in writer_responses:
            logger.debug(f"Writer response: {response.content}")

        yield from writer_responses

        # Save the blog post in the session state for future runs
        if "blog_posts" not in self.session_state:
            self.session_state["blog_posts"] = []
        self.session_state["blog_posts"].append(
            {"topic": topic, "blog_post": self.writer.run_response.content}
        )

class ContentGenerationToolkit(Toolkit):
    def __init__(self, name: str = "content_generation_toolkit"):
        super().__init__(name=name)
        self.workflow = None
    
    def initialize_workflow(self, session_id: str, storage: SqlWorkflowStorage):
        self.workflow = ContentGenerationWorkflow(session_id=session_id, storage=storage)
        self.register(self.generate_blog_post)
    
    def generate_blog_post(self, topic: str, use_cache: bool = True) -> Iterator[RunResponse]:
        if self.workflow is None:
            raise ValueError("Workflow not initialized. Call initialize_workflow first.")
        return self.workflow.run(topic, use_cache)
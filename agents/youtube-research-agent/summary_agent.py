import os
import sys
from pathlib import Path
import time
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Now we can import from tools
from tools.youtube_toolkit import YoutubeTools
from tools.transcribe_toolkit import TranscriptionTools

import json
from typing import Optional, Iterator, List
from pydantic import BaseModel, Field
from pathlib import Path

from phi.agent import Agent
from phi.workflow import Workflow, RunResponse, RunEvent
from phi.storage.workflow.sqlite import SqlWorkflowStorage
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.firecrawl import FirecrawlTools
from phi.utils.pprint import pprint_run_response
from phi.utils.log import logger
from dotenv import load_dotenv

# Import settings for URLs and research parameters
from config.settings import (
    YOUTUBE_URLS,
    MAX_THEMES_TO_RESEARCH,
    ARTICLES_PER_THEME,
    SEARCH_DELAY
)

# Define base output directory relative to the script location
SCRIPT_DIR = Path(__file__).parent
BASE_OUTPUT_DIR = SCRIPT_DIR / "summary-agent-output"

# File paths (relative to base output directory)
AUDIO_DIR = BASE_OUTPUT_DIR / "audio"
TRANSCRIPTION_SUMMARY_DIR = BASE_OUTPUT_DIR / "transcription_summary"
TRANSCRIPTION_OUTPUT_DIR = BASE_OUTPUT_DIR / "transcriptions"
OUTPUT_DIR = BASE_OUTPUT_DIR / "agent-output"

# Create directories if they don't exist
BASE_OUTPUT_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)
TRANSCRIPTION_SUMMARY_DIR.mkdir(exist_ok=True)
TRANSCRIPTION_OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

print([e.name for e in RunEvent])

# Load environment variables
load_dotenv()

class NewsArticle(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(None, description="Summary of the article if available.")

class SearchResults(BaseModel):
    articles: List[NewsArticle]

class TranscriptionAnalysis(BaseModel):
    executive_summary: str = Field(..., description="Brief overview of the main points (2-3 sentences)")
    detailed_summary: str = Field(..., description="Comprehensive breakdown of the content, organized by major topics")
    key_themes: List[str] = Field(..., description="Key themes and topics extracted from the content")
    key_insights: List[str] = Field(..., description="Specific insights, quotes, or notable points")
    recommendations: Optional[List[str]] = Field(None, description="Action items or recommendations if applicable")

class ContentSummaryAgent(Workflow):
    # Tools for handling YouTube content
    youtube_tool: Agent = Agent(
        tools=[YoutubeTools()],
        instructions=[
            "Download audio from YouTube URLs",
            "Save audio files to the project's audio directory"
        ]
    )
    
    transcription_tool: Agent = Agent(
        tools=[TranscriptionTools()],
        instructions=[
            "Transcribe audio files to text",
            "Extract speaker information and full conversation content",
            "Save transcriptions to JSON format"
        ]
    )
    
    analyzer: Agent = Agent(
        instructions=[
            "Analyze transcription content and generate a detailed, structured analysis",
            "Structure your analysis with the following sections:",
            "1. Executive Summary: Concise overview of the main discussion points",
            "2. Detailed Summary: Break down the content into logical sections with clear headings",
            "3. Key Themes: Identify 3-5 major themes or topics",
            "4. Key Insights: Extract 5-7 specific insights, quotes, or notable points",
            "5. Recommendations: If applicable, provide actionable takeaways",
            "Focus on technical accuracy and practical implications",
            "Use clear formatting and structure in each section"
        ],
        response_model=TranscriptionAnalysis
    )

    # Research tools
    searcher: Agent = Agent(
        tools=[DuckDuckGo()],
        instructions=[
            "Search for recent and relevant articles based on provided themes",
            "Focus on high-quality technical analysis and industry insights",
            "Return only the 5 most relevant articles",
            "Prioritize authoritative sources"
        ],
        response_model=SearchResults,
    )

    crawler: Agent = Agent(
        tools=[FirecrawlTools(scrape=True, crawl=True)],
        instructions=[
            "Analyze each article URL in depth",
            "Extract key information and technical details",
            "Focus on data, statistics, and specific examples",
            "Identify market trends and industry implications"
        ],
    )

    writer: Agent = Agent(
        instructions=[
            "Generate a comprehensive analysis combining transcription insights and research",
            "Structure the content with clear sections and subsections",
            "Include key takeaways and future implications",
            "Maintain focus on technical accuracy and practical insights",
            "Cite sources and reference specific examples",
            "Ensure all information from the detailed summaries is incorporated"
        ],
    )

    def run(self, url: Optional[str] = None, topic: Optional[str] = None) -> Iterator[RunResponse]:
        if url:
            logger.info(f"Processing YouTube content from: {url}")
            
            # Step 1: Download audio
            logger.info("Step 1: Downloading audio")
            try:
                result = self.youtube_tool.run(f"download_audio('{url}')")
                logger.info(f"Download result: {result.content}")
                
                # Check if download was successful
                if "error" in str(result.content).lower() or "failed" in str(result.content).lower():
                    logger.error(f"Download failed: {result.content}")
                    yield RunResponse(
                        run_id=self.run_id,
                        event=RunEvent.run_completed,
                        content=f"Error downloading audio: {result.content}"
                    )
                    return
                    
                # Update: Look for audio files in the correct directory
                audio_dir = BASE_OUTPUT_DIR / "audio"  # Use the constant defined at the top
                audio_files = list(audio_dir.glob('*.mp3'))
                
                if not audio_files:
                    logger.error("No audio files found after reported successful download")
                    yield RunResponse(
                        run_id=self.run_id,
                        event=RunEvent.run_completed,
                        content="Error: No audio file found after download"
                    )
                    return
                    
                logger.info(f"Found audio file: {audio_files[0].name}")
                
            except Exception as e:
                logger.error(f"Error during download: {str(e)}")
                yield RunResponse(
                    run_id=self.run_id,
                    event=RunEvent.run_completed,
                    content=f"Error during download: {str(e)}"
                )
                return

            # Step 2: Transcribe audio
            try:
                logger.info("Step 2: Transcribing audio")
                actual_file = next(AUDIO_DIR.glob('*.mp3'))
                
                logger.info(f"Transcribing audio file: {actual_file.name}")
                transcription_result = self.transcription_tool.run(f"transcribe_audio('{actual_file.name}')")
                
                # Modified transcription handling
                if isinstance(transcription_result.content, str):
                    if "error" in transcription_result.content.lower():
                        raise ValueError(transcription_result.content)
                        
                    # Extract content from JSON if it's in JSON format
                    if transcription_result.content.strip().startswith('{'):
                        try:
                            json_content = json.loads(transcription_result.content)
                            transcript_text = json_content.get('transcription', {}).get('content', '')
                        except json.JSONDecodeError:
                            transcript_text = transcription_result.content
                    else:
                        transcript_text = transcription_result.content
                        
                    logger.info("Successfully received transcript text")
                    logger.debug(f"Transcript text (first 100 chars): {transcript_text[:100]}...")
                else:
                    raise ValueError(f"Expected string response, got: {type(transcription_result.content)}")
                    
            except Exception as e:
                logger.error(f"Error during transcription: {str(e)}", exc_info=True)
                yield RunResponse(
                    run_id=self.run_id,
                    event=RunEvent.run_completed,
                    content=f"Error during transcription: {str(e)}"
                )
                return

            # Step 3: Analyze transcription
            try:
                logger.info("Step 3: Analyzing transcription")
                analysis_response = self.analyzer.run(transcript_text)
                
                # Create transcription_summary directory if it doesn't exist
                summary_dir = Path(__file__).parent.parent / TRANSCRIPTION_SUMMARY_DIR
                summary_dir.mkdir(exist_ok=True)
                
                # Save analysis to JSON file using the same filename as the audio/transcription
                summary_data = {
                    "executive_summary": analysis_response.content.executive_summary,
                    "detailed_summary": analysis_response.content.detailed_summary,
                    "key_themes": analysis_response.content.key_themes,
                    "key_insights": analysis_response.content.key_insights,
                    "recommendations": analysis_response.content.recommendations,
                    "analyzed_at": time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                summary_file = summary_dir / f"{actual_file.stem}_summary.json"
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump(summary_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Analysis saved to: {summary_file}")
                
                # Step 4: Research each theme (limited by MAX_THEMES_TO_RESEARCH)
                logger.info("Step 4: Researching themes")
                for theme in summary_data['key_themes'][:MAX_THEMES_TO_RESEARCH]:
                    logger.info(f"Researching theme: {theme}")
                    yield from self._research_topic(theme)

            except Exception as e:
                logger.error(f"Error analyzing transcription: {str(e)}", exc_info=True)
                yield RunResponse(
                    run_id=self.run_id,
                    event=RunEvent.run_completed,
                    content=f"Error analyzing transcription: {str(e)}"
                )
                return

        elif topic:
            yield from self._research_topic(topic)
        
        else:
            logger.error("No URL or topic provided")
            yield RunResponse(
                run_id=self.run_id,
                event=RunEvent.run_completed,
                content="Either URL or topic must be provided"
            )

    def _research_topic(self, topic: str) -> Iterator[RunResponse]:
        logger.info(f"Researching topic: {topic}")
        
        # Add delay between searches
        time.sleep(SEARCH_DELAY)
        
        # Step 1: Search for articles (limited by ARTICLES_PER_THEME)
        searcher_response = self.searcher.run(topic)
        if not searcher_response or not searcher_response.content:
            yield RunResponse(
                run_id=self.run_id,
                event=RunEvent.run_completed,
                content=f"No articles found for topic: {topic}"
            )
            return

        # Step 2: Analyze articles (with rate limiting)
        detailed_summaries = []
        successful_scrapes = 0
        failed_scrapes = 0
        
        for article in searcher_response.content.articles[:ARTICLES_PER_THEME]:
            try:
                logger.info(f"Attempting to scrape: {article.url}")
                
                if article.url.lower().endswith('.pdf'):
                    logger.info(f"Skipping PDF URL: {article.url}")
                    continue
                    
                crawler_response = self.crawler.run(
                    f"Provide a brief, focused analysis of the key points from {article.url} "
                    f"that are specifically relevant to {topic}. Limit to 2-3 paragraphs."
                )
                
                if crawler_response and crawler_response.content:
                    successful_scrapes += 1
                    logger.info(f"Successfully scraped: {article.url}")
                    detailed_summaries.append({
                        "url": article.url,
                        "title": article.title,
                        "detailed_summary": crawler_response.content
                    })
                time.sleep(SEARCH_DELAY)  # Add delay between article scrapes
                
            except Exception as e:
                failed_scrapes += 1
                logger.warning(f"Failed to scrape {article.url}: {str(e)}")
        
        logger.info(f"Scraping complete. Successful: {successful_scrapes}, Failed: {failed_scrapes}")

        # Step 3: Generate research analysis
        writer_input = {
            "topic": topic,
            "articles": [v.model_dump() for v in searcher_response.content.articles],
            "detailed_summaries": detailed_summaries
        }
        
        # Only yield the writer's response once
        writer_response = self.writer.run(json.dumps(writer_input))
        if writer_response and writer_response.content:
            yield RunResponse(
                run_id=self.run_id,
                event=RunEvent.run_completed,
                content=writer_response.content
            )


if __name__ == "__main__":
    agent = ContentSummaryAgent(
        session_id="content-summary-agent",
        storage=SqlWorkflowStorage(
            table_name="content_summary_workflows",
            db_file="tmp/workflows.db",
        ),
    )
    
    # Track processed URLs
    processed_urls = []
    failed_urls = []
    
    # Process each URL in the config
    for url in YOUTUBE_URLS:
        logger.info(f"\nProcessing URL: {url}")
        
        try:
            # Run the agent for this URL
            results = list(agent.run(url=url))
            
            # Get the audio filename to match transcription naming
            audio_dir = Path(__file__).parent.parent / AUDIO_DIR
            audio_files = list(audio_dir.glob('*.mp3'))
            
            if not audio_files:
                logger.error("No audio files found to create output")
                continue
                
            audio_file = audio_files[0]
            base_name = audio_file.stem
            
            # Get the transcription summary
            summary_dir = Path(__file__).parent.parent / TRANSCRIPTION_SUMMARY_DIR
            summary_file = summary_dir / f"{base_name}_summary.json"
            
            # Create output directory if it doesn't exist
            output_dir = Path(__file__).parent.parent / OUTPUT_DIR
            output_dir.mkdir(exist_ok=True)
            
            # Save results to markdown file using same base name
            output_file = output_dir / f"{base_name}.md"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                # First write the transcription summary if it exists
                if summary_file.exists():
                    with open(summary_file, 'r', encoding='utf-8') as sf:
                        summary_data = json.load(sf)
                        f.write("# Video Summary\n\n")
                        f.write("## Executive Summary\n")
                        f.write(f"{summary_data['executive_summary']}\n\n")
                        f.write("## Detailed Summary\n")
                        f.write(f"{summary_data['detailed_summary']}\n\n")
                        f.write("## Key Themes\n")
                        for theme in summary_data['key_themes']:
                            f.write(f"- {theme}\n")
                        f.write("\n")
                        f.write("## Key Insights\n")
                        for insight in summary_data['key_insights']:
                            f.write(f"- {insight}\n")
                        f.write("\n")
                        f.write("## Recommendations\n")
                        for rec in summary_data['recommendations']:
                            f.write(f"- {rec}\n")
                        f.write("\n---\n\n")
                
                # Then write the research results
                f.write("# Research Analysis\n\n")
                for response in results:
                    if response.content:
                        f.write(f"{response.content}\n\n")
            
            # Print results
            pprint_run_response(results, markdown=True)
            
            # Clean up audio file after processing this URL
            if audio_file.exists():
                logger.info(f"Cleaning up audio file: {audio_file.name}")
                audio_file.unlink()
            
            # Mark URL as processed
            processed_urls.append(url)
            logger.info(f"Successfully processed URL: {url}")
            
        except Exception as e:
            logger.error(f"Error processing URL {url}: {str(e)}")
            failed_urls.append(url)
            continue
    
    # Final summary
    logger.info("\n=== Processing Summary ===")
    logger.info(f"Total URLs: {len(YOUTUBE_URLS)}")
    logger.info(f"Successfully processed: {len(processed_urls)}")
    logger.info(f"Failed: {len(failed_urls)}")
    
    if failed_urls:
        logger.info("\nFailed URLs:")
        for url in failed_urls:
            logger.info(f"- {url}")
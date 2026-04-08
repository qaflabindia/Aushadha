import os
import sys
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import SessionLocal
from src.ui_translations import UITranslation, upsert_ui_translation

# The English phrases from i18n.ts (as of the user's report)
PHRASES = {
    "fileManagement": "File Management",
    "clinicalIntelligence": "Clinical Intelligence",
    "dbConnection": "DB Connection",
    "noGraphSchema": "No Graph Schema configured",
    "name": "Name",
    "status": "Status",
    "uploadStatus": "Upload Status",
    "sizeKB": "Size (KB)",
    "source": "Source",
    "type": "Type",
    "model": "Model",
    "nodes": "Nodes",
    "completed": "Completed",
    "uploaded": "Uploaded",
    "localFile": "local file",
    "generateGraph": "Generate Graph",
    "deleteFiles": "Delete Files",
    "previewGraph": "Preview Graph",
    "graphSettings": "Graph Settings",
    "llmModel": "LLM Model for Processing & Chat",
    "processingAndChat": "Processing & Chat",
    "intelligenceSearch": "Intelligence Search",
    "medicalIntelligence": "Medical Intelligence",
    "selectLanguage": "Select Language",
    "dataInsights": "Data Insights",
    "knowledgeGraph": "Knowledge Graph",
    "secretVault": "Secret Vault",
    "generatedGraph": "Generated Graph",
    "chunksInfo": "We are visualizing 50 chunks at a time",
    "documentChunk": "Document & Chunk",
    "entities": "Entities",
    "resultOverview": "Result Overview",
    "totalNodes": "Total Nodes",
    "relationships": "Relationships",
    "searchNodes": "Search On Node Properties",
    "inquireVault": "Inquire Vault Intelligence",
    "authorizedTerminal": "Authorized Terminal",
    "conciergeIntelligence": "Concierge Intelligence",
    "details": "Details",
    "show": "Show",
    "page": "Page",
    "largFilesWarning": "Large files may be partially processed up to 10K characters due to resource limit.",
    "welcomeMessage": "Welcome to Concierge Intelligence. You can ask questions related to documents which have been completely processed.",
    "neuralNetwork": "AyushPragya Medical Neural Network",
    "deleteFile": "Select one or more files to delete",
    "showGraph": "Preview generated graph.",
    "bloomGraph": "Visualize the graph in Bloom",
    "deleteSelectedFiles": "File/Files to be deleted",
    "documentation": "Documentation",
    "github": "GitHub Issues",
    "theme": "Light / Dark mode",
    "settings": "Entity Graph Extraction Settings",
    "chat": "Start a chat",
    "sources": "Upload files",
    "deleteChat": "Delete",
    "maximise": "Maximise",
    "minimise": "Minimise",
    "copy": "Copy to Clipboard",
    "copied": "Copied",
    "stopSpeaking": "Stop Speaking",
    "textTospeech": "Text to Speech",
    "createSchema": "Define schema from text",
    "useExistingSchema": "Fetch schema from database",
    "clearChat": "Clear Chat History",
    "continue": "Continue",
    "clearGraphSettings": "Clear configured Graph Schema",
    "applySettings": "Apply Graph Schema",
    "openChatPopout": "Chat",
    "downloadChat": "Download Conversation",
    "visualizeGraph": "Visualize Graph Schema",
    "close": "Close",
    "additionalInstructions": "Analyze instructions for schema",
    "predinedSchema": "Predefined Schema",
    "dataImporterJson": "Data Importer JSON",
    "exploreGraphWithBloom": "Explore Graph",
    "showPreviewGraph": "Preview Graph",
    "dropzoneSpan": "Documents, Images, Unstructured text",
    "youtube": "Youtube",
    "gcs": "GCS",
    "amazon": "Amazon S3",
    "noLables": "No Labels Found in the Database",
    "dropYourCreds": "Drop your neo4j credentials file here",
    "analyze": "Analyze text to extract graph schema",
    "connect": "Connect",
    "disconnect": "Disconnect",
    "submit": "Submit",
    "connectToDB": "Connect to DB",
    "cancel": "Cancel",
    "detailsSettings": "Details",
    "continueSettings": "Continue",
    "clearSettings": "Clear Schema",
    "ask": "Ask",
    "applyGraphSchema": "Apply",
    "provideAdditionalInstructions": "Provide Additional Instructions for Entity Extractions",
    "analyzeInstructions": "Analyze Instructions",
    "helpInstructions": "Provide specific instructions for entity extraction, such as focusing on the key topics.",
    "importDropzoneSpan": "JSON Documents",
    "filesProcessingSelectionWarning": "Files are still processing, please select individual checkbox for deletion",
    "cancelProcessingJob": "Cancel the processing job",
    "entityExtractionSettings": "Entity Extraction Settings",
    "disconnectedNodes": "Disconnected Nodes",
    "duplicationNodes": "Duplication Nodes",
    "postProcessingJobs": "Post Processing Jobs",
    "allFiles": "All Files",
    "completedFiles": "Completed Files",
    "newFiles": "New Files",
    "failedFiles": "Failed Files",
    "allSources": "All Sources",
    "allTypes": "All Types",
    "all": "All",
    "actions": "Actions",
    "generationCancelled": "Generation cancelled by user.",
    "translationFailed": "Translation failed. Please try again.",
    "speechSynthesisFailed": "Speech synthesis failed. Please try again.",
    "processingArchitecture": "Processing Architecture...",
    "intelligenceSearchMode": "Intelligence Search Mode",
    "retrievalInformation": "Retrieval information",
    "toGenerateThisResponse": "To generate this response, the process took",
    "seconds": "seconds",
    "utilizing": "utilizing",
    "tokensWithTheModel": "tokens with the model",
    "communities": "Communities",
    "sourcesUsed": "Sources used",
    "topEntitiesUsed": "Top Entities used",
    "generatedCypherQuery": "Generated Cypher Query",
    "evaluationMetrics": "Evaluation Metrics",
    "generatedGraphTitle": "Generated Graph",
    "relevancy": "Relevancy",
    "faithfulness": "Faithful",
    "answer_relevancy": "Relevancy",
    "context_entity_recall": "Context",
    "semantic_score": "Semantic",
    "rouge_score": "Rouge",
    "mode": "Mode",
    "noSourcesFound": "No Sources Found",
    "noChunksFound": "No Chunks Found",
    "noEntitiesFound": "No Entities Found",
    "noCommunitiesFound": "No Communities Found",
    "similarityScore": "Similarity Score",
    "viewGraph": "View Graph",
    "id": "ID",
    "vectorMode": "vector",
    "graphMode": "graph",
    "graphVectorMode": "graph+vector",
    "fulltextMode": "fulltext",
    "graphVectorFulltextMode": "graph+vector+fulltext",
    "entityVectorMode": "entity search+vector",
    "globalVectorMode": "global search+vector+fulltext",
    "clinicalMode": "AYUSH Clinical",
    "live": "LIVE",
    "selected": "Selected",
    "dbWelcomeMessage": "Welcome to the DB Knowledge Graph Chat. You can ask questions related to documents which have been completely processed.",
    "getMoreMetrics": "Get More Metrics by providing reference answer",
    "metric": "Metric",
    "score": "Score",
    "notAvailable": "N.A",
    "translationManagement": "Translation Management",
    "language": "Language",
    "coverage": "Coverage",
    "untranslated": "Untranslated",
    "seedNow": "Seed Now",
    "prewarming": "Pre-warming...",
    "seedingCompleted": "Seeding completed",
    "Patient Insights": "Patient Insights",
    "Global Research": "Global Research",
    "Administration": "Administration",
    "AI Assistant": "AI Assistant",
    "Settings / Account": "Settings / Account",
    "Workspace Settings": "Workspace Settings",
    "General Workstation": "General Workstation",
    "Interface Language": "Interface Language",
    "Theme": "Theme",
    "Logout": "Logout",
    "LLM Model": "LLM Model",
    "Select Model": "Select Model",
    "Chat Retrieval Mode": "Chat Retrieval Mode",
    "Configure Sources": "Configure Sources",
    "Secret Name": "Secret Name",
    "Secret Value": "Secret Value",
    "Save Secret": "Save Secret",
    "Configured Secrets": "Configured Secrets",
    "Load": "Load",
    "Change Password": "Change Password",
    "New Password": "New Password",
    "Confirm New Password": "Confirm New Password",
    "Update Password": "Update Password",
    "General": "General",
    "Graph Settings": "Graph Settings",
    "Settings": "Settings",
    "Workspace Control Center": "Workspace Control Center",
}

def seed():
    db = SessionLocal()
    count = 0
    try:
        for key, english_phrase in PHRASES.items():
            # Ensure the English phrase exists as an english_key in the DB
            # We use the phrase itself as the key.
            row = db.query(UITranslation).filter(UITranslation.english_key == english_phrase).first()
            if not row:
                row = UITranslation(english_key=english_phrase, en=english_phrase)
                db.add(row)
                count += 1
                print(f"Added: {english_phrase}")
            
            # Legacy support: also ensure the camelCase key exists if it's different
            if key != english_phrase:
                row_legacy = db.query(UITranslation).filter(UITranslation.english_key == key).first()
                if not row_legacy:
                    row_legacy = UITranslation(english_key=key, en=english_phrase)
                    db.add(row_legacy)
                    count += 1
                    print(f"Added Legacy: {key} -> {english_phrase}")
        
        db.commit()
        print(f"Seeding completed. {count} rows added/verified.")
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()

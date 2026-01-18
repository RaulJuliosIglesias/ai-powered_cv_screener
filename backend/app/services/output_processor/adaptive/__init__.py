"""
ADAPTIVE OUTPUT PROCESSOR - Smart Dynamic Structures & Modules

This package implements the INTELLIGENT ADAPTIVE system for queries that don't fit
predefined rigid structures. Unlike rigid modules, these components:

1. DETECT dynamically what the user is asking
2. INFER the schema (columns, attributes) from query + data
3. BUILD tables with variable columns based on context
4. GENERATE analysis adapted to the specific question
5. ASSEMBLE structures that change every time

ARCHITECTURE:
============

┌─────────────────────────────────────────────────────────────────┐
│                    AdaptiveStructureBuilder                      │
│  (Main orchestrator - assembles all components dynamically)      │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ QueryAnalyzer   │  │ SchemaInference │  │ DataExtractor   │
│ - Detect intent │  │ - Infer columns │  │ - Extract from  │
│ - Find attrs    │  │ - Determine fmt │  │   chunks        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
         ┌────────────────────┴────────────────────┐
         ▼                                         ▼
┌─────────────────────────┐          ┌─────────────────────────┐
│  DynamicTableGenerator  │          │ AdaptiveAnalysisGen     │
│  - Variable columns     │          │ - Contextual analysis   │
│  - Format selection     │          │ - Distribution stats    │
│  - Smart sorting        │          │ - Key findings          │
└─────────────────────────┘          └─────────────────────────┘

KEY PRINCIPLES:
==============
- NO HARDCODED COLUMNS: Table schema is inferred at runtime
- NO FIXED FORMATS: Output format adapts to data characteristics
- NO PREDEFINED TEMPLATES: Analysis text is generated from data
- SCHEMA-LESS: Works with any attribute combination
- SELF-DESCRIBING: Output includes metadata about its own structure

USAGE:
======
    from app.services.output_processor.adaptive import AdaptiveStructureBuilder
    
    builder = AdaptiveStructureBuilder()
    result = builder.build(
        query="What technologies do candidates have?",
        chunks=retrieved_chunks,
        llm_output=raw_llm_response
    )
    
    # Result is a fully dynamic structure with:
    # - direct_answer: Generated summary
    # - dynamic_table: Table with inferred columns
    # - analysis: Contextual analysis
    # - conclusion: Data-driven conclusion
"""

from .analysis_generator import AdaptiveAnalysisGenerator
from .data_extractor import SmartDataExtractor
from .query_analyzer import QueryAnalyzer
from .schema_inference import SchemaInferenceEngine
from .structure_builder import AdaptiveStructureBuilder
from .table_generator import DynamicTableGenerator

__all__ = [
    "QueryAnalyzer",
    "SchemaInferenceEngine", 
    "SmartDataExtractor",
    "DynamicTableGenerator",
    "AdaptiveAnalysisGenerator",
    "AdaptiveStructureBuilder",
]

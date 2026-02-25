# Voice Brief Assistant - Quick Start Guide

## What It Does

The Voice Brief Assistant helps you refine your marketing campaign brief through natural voice conversation. It asks clarifying questions about your target audience, campaign goals, messaging, and more - just like talking to a marketing strategist.

## Quick Start

### Step 1: Set Up API Key

1. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a `.env` file in the frontend directory:
   ```bash
   VITE_GEMINI_API_KEY=your_api_key_here
   ```
3. Restart your development server

### Step 2: Access the Assistant

**Option A: Floating Widget (Recommended)**
1. Navigate to the Trends page (`/trends`)
2. Click "Voice Brief Assistant" button (top-right corner)
3. The assistant appears as a floating widget

**Option B: Full Page**
1. Click "Voice Assistant" in the sidebar
2. Or navigate directly to `/voice`

### Step 3: Start Conversation

1. Click **"Connect & Record"** button
2. Allow microphone access when prompted
3. Start speaking about your campaign
4. The assistant will respond with clarifying questions

### Step 4: Have a Conversation

**Example Conversation Flow:**

```
You: "I'm planning a campaign for our new smartphone"
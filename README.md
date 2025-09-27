# AI Personal Trainer 💪

A Streamlit-based personal trainer that lets you log workouts in natural language, track your progress, and get AI-powered coaching advice.

## Features

- 📝 Natural language workout logging
- 📊 Progress tracking and analytics
- 🤖 AI-powered coaching
- 📈 Visual progress charts
- 💾 CSV export
- 🗑️ Easy workout management

## Two Versions Available

### 1. Local Version (with Ollama)
- Uses Ollama with Mistral model locally
- Best for privacy and no usage limits
- Requires Ollama installation
- Files: `app.py` + `llm.py`

### 2. Cloud Version (with Hugging Face)
- Uses Hugging Face's API (flan-t5-large model)
- Perfect for Streamlit Cloud deployment
- Requires Hugging Face API key
- Files: `app2.py` + `llm2.py`

## Setup Instructions

### Local Version Setup
1. Install Python requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Install Ollama from [ollama.ai](https://ollama.ai)

3. Run the app:
   ```bash
   streamlit run app.py
   ```

### Cloud Version Setup
1. Install Python requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Get your Hugging Face API key:
   - Go to [Hugging Face](https://huggingface.co)
   - Create an account if needed
   - Get your API key from https://huggingface.co/settings/tokens

3. Set up your API key in one of two ways:
   - Create `.streamlit/secrets.toml` with:
     ```toml
     HUGGINGFACE_API_KEY = "your-api-key-here"
     ```
   - Or enter it in the app's UI when prompted

4. Run the cloud version:
   ```bash
   streamlit run app2.py
   ```

## Usage

1. Log workouts in natural language:
   - "Did 3 sets of 10 pushups"
   - "Bench press 5x5 @ 100kg"
   - "4 sets of squats with 20kg, did 8,8,7,7 reps"

2. View your workout history in the Logs tab

3. Check your progress in the Analytics tab

4. Get AI coaching advice in the Coach tab

## Deployment

### Local Deployment
- Run locally for unlimited usage
- Perfect for personal use
- No API key needed

### Detailed Deployment Guide

#### 1. GitHub Setup
1. Create a GitHub account if you don't have one
2. Create a new repository:
   - Go to https://github.com/new
   - Name your repository (e.g., `ai-personal-trainer`)
   - Make it Public
   - Don't initialize with any files

3. Push your code to GitHub:
   ```bash
   # Initialize git in your project folder
   git init
   
   # Add all files
   git add .
   
   # Commit the files
   git commit -m "Initial commit"
   
   # Add your GitHub repository as remote
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   
   # Push to GitHub
   git push -u origin main
   ```

#### 2. Streamlit Cloud Setup
1. Go to https://streamlit.io/cloud
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository and branch
5. Set the main file path to `app2.py`
6. Click "Deploy!"

#### 3. Adding Hugging Face API Key
1. Get your API key:
   - Go to https://huggingface.co/settings/tokens
   - Copy your API token

2. Add to Streamlit Cloud:
   - In your deployed app page, click ⋮ (three dots menu)
   - Select "Settings"
   - Go to "Secrets"
   - Click "Add a new secret"
   - Enter:
     - Key: `HUGGINGFACE_API_KEY`
     - Value: Your API key from Hugging Face
   - Click "Save"

3. Verify Setup:
   - Your app will automatically reboot
   - Test by logging a workout
   - The AI features should now work

#### 4. Updating Your App
1. Make changes to your local code
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push
   ```
3. Streamlit Cloud will automatically redeploy

#### 5. Troubleshooting
- If the app shows API key errors:
  - Check the secret name is exactly `HUGGINGFACE_API_KEY`
  - Verify the API key is valid
  - Try redeploying the app
- If the app fails to deploy:
  - Check the logs in Streamlit Cloud
  - Verify all requirements are in `requirements.txt`
  - Ensure `app2.py` is in the root directory

## Limitations

### Local Version
- Requires Ollama installation
- Uses more local resources
- Slower first run (model download)

### Cloud Version
- Requires API key
- Subject to API rate limits (30,000 requests/month free tier)
- Slightly faster response times

## Contributing

Feel free to open issues or submit pull requests for:
- New features
- Bug fixes
- Documentation improvements
- UI enhancements

## License

MIT License - feel free to use and modify!
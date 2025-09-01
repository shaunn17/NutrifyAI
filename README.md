# 🥗 AI-Powered Healthy Recipe & Macro Calculator

A smart recipe generator that creates personalized healthy recipes from your available ingredients and provides detailed nutritional macro analysis. Built with Streamlit, Groq AI, and USDA FoodData Central API.

![Python](https://img.shields.io/badge/python-v3.7+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-latest-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- **🤖 AI Recipe Generation**: Uses Groq's Llama-3.1-8B-Instant model to create customized recipes from your ingredients
- **📊 Nutritional Analysis**: Fetches accurate macro data (protein, carbs, fat, fiber) from USDA FoodData Central
- **🍽️ Smart Portioning**: Calculates macros per serving and total recipe
- **🎯 Ingredient-Only Recipes**: Creates recipes using ONLY the ingredients you provide
- **📱 Clean UI**: Modern, responsive Streamlit interface with beautiful animations
- **🗄️ Recipe Database**: SQLite database to store, search, and manage your recipes
- **⭐ Favorites & Ratings**: Rate recipes and save favorites for easy access
- **📚 Recipe History**: Browse, search, and revisit all your generated recipes
- **🔍 Recipe Filtering**: Filter recipes by dietary restrictions, cuisine type, meal type, cooking time, and difficulty level
- **📈 Analytics**: Track your recipe generation stats and success rates
- **⚡ Fast & Free**: Leverages free APIs for cost-effective operation

## 🚀 Demo

Simply enter your available ingredients (e.g., "chicken breast, quinoa, spinach, olive oil, garlic") and get:

1. **Complete Recipe** with cooking instructions
2. **Macro Breakdown** per ingredient 
3. **Per-Serving Nutrition** for meal planning
4. **Total Recipe Macros** for batch cooking
5. **Automatic Database Storage** for future reference
6. **Rating & Favorites** system for recipe management
7. **Smart Recipe Filtering** to find recipes by category

## 🛠️ Installation

### Prerequisites

- Python 3.7 or higher
- Free API keys from Groq and USDA

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-recipe-app.git
   cd ai-recipe-app
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Get your free API keys**
   
   **Groq API Key** (for AI recipe generation):
   - Visit [console.groq.com](https://console.groq.com)
   - Sign up/login and create an API key
   
   **USDA API Key** (for nutritional data):
   - Visit [fdc.nal.usda.gov/api-guide.html](https://fdc.nal.usda.gov/api-guide.html)
   - Sign up for a free API key

4. **Configure your API keys**
   
   Create `.streamlit/secrets.toml`:
   ```toml
   groq_api_key = "your_groq_api_key_here"
   usda_api_key = "your_usda_api_key_here"
   ```

5. **Run the application**
   ```bash
   streamlit run app.py
   ```

The app will open in your browser at `http://localhost:8501`

## 🔧 Configuration

### Environment Variables (Alternative)

Instead of using `secrets.toml`, you can set environment variables:

```bash
export GROQ_API_KEY="your_groq_api_key_here"
export USDA_API_KEY="your_usda_api_key_here"
```

### Deployment

For deployment on Streamlit Cloud or other platforms, add your API keys to the platform's secrets management:

- `groq_api_key`: Your Groq API key
- `usda_api_key`: Your USDA API key

## 📖 Usage

### Basic Usage

1. **Enter Ingredients**: Type your available ingredients separated by commas
   ```
   chicken breast, quinoa, spinach, olive oil, garlic
   ```

2. **Generate Recipe**: Click "Generate Recipe" to get your AI-created recipe

3. **Review Results**: 
   - Recipe title and serving size
   - Ingredient quantities in grams
   - Step-by-step cooking instructions
   - Detailed macro breakdown

### Recipe Filtering & Discovery

After generating recipes, use the **Recipe Filtering & Categories** section to:

1. **Select Filters**: Choose from:
   - **🥗 Dietary Restrictions**: None, Vegetarian, Vegan, Keto, Paleo
   - **🌍 Cuisine Types**: Italian, Asian, Mexican, Mediterranean, American, Indian, French, Thai
   - **🍽️ Meal Types**: Breakfast, Lunch, Dinner, Snacks, Desserts
   - **⏱️ Cooking Time**: Quick (15min), Medium (30min), Long (60min+)
   - **📚 Difficulty Level**: Beginner, Intermediate, Advanced

2. **Apply Filters**: Click "Apply Filters" to find matching recipes from your saved collection

3. **Browse Results**: View filtered recipes with ratings, favorites, and nutrition info

**Example**: Filter for "Vegetarian" + "Italian" + "Dinner" + "Medium" + "Beginner" to find all your saved vegetarian Italian dinner recipes that are medium difficulty and beginner-friendly.

### Example Input/Output

**Input:**
```
salmon, sweet potato, broccoli, olive oil, lemon
```

**Output:**
- **Recipe**: "Roasted Salmon with Sweet Potato and Broccoli" (4 servings)
- **Macros per serving**: ~35g protein, 25g carbs, 12g fat, 6g fiber
- **Cooking steps**: Detailed preparation and cooking instructions

## 🏗️ Architecture

```
ai_recipe_app/
├── app.py              # Main Streamlit application with UI and filtering
├── database.py         # SQLite database with filtering capabilities
├── utils.py            # USDA API integration and macro calculations
├── requirements.txt    # Python dependencies
└── .streamlit/
    └── secrets.toml    # API keys configuration
```

### Key Components

- **`app.py`**: Main application with Streamlit UI, Groq AI integration, and recipe filtering system
- **`database.py`**: SQLite database management with filtering and search capabilities
- **`utils.py`**: USDA FoodData Central API wrapper for nutritional data
- **Pydantic Models**: Structured data validation for recipes
- **Error Handling**: Graceful handling of API failures and invalid inputs

## 🔌 APIs Used

### Groq API
- **Model**: Llama-3.1-8B-Instant
- **Purpose**: Recipe generation from ingredients
- **Rate Limit**: Generous free tier
- **Documentation**: [console.groq.com](https://console.groq.com)

### USDA FoodData Central
- **Purpose**: Nutritional data lookup
- **Coverage**: 200,000+ food items
- **Rate Limit**: 1,000 requests/hour (free)
- **Documentation**: [fdc.nal.usda.gov](https://fdc.nal.usda.gov/api-guide.html)

## 🧪 Technical Details

### Recipe Generation Process

1. **Input Validation**: Parses and validates ingredient list
2. **AI Prompt**: Constructs structured prompt for Groq AI
3. **JSON Parsing**: Extracts and validates recipe JSON
4. **Macro Calculation**: Queries USDA API for each ingredient
5. **Scaling**: Calculates per-serving and total macros

### Data Flow

```mermaid
graph LR
    A[User Input] --> B[Groq AI]
    B --> C[Recipe JSON]
    C --> D[USDA API]
    D --> E[Macro Data]
    E --> F[Final Output]
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔮 Future Enhancements

- [x] Recipe rating and favorites system ✅
- [x] Dietary restriction filters (vegan, keto, etc.) ✅
- [ ] Shopping list generation
- [ ] Recipe image generation
- [ ] Meal planning calendar
- [ ] Export to PDF/email
- [ ] Ingredient substitution suggestions
- [ ] Calorie target optimization

## 🆘 Troubleshooting

### Common Issues

**"Please add your API keys in Secrets"**
- Ensure your `secrets.toml` file is in the `.streamlit/` directory
- Verify API keys are correctly formatted (no extra spaces/quotes)

**"No USDA match found"**
- Try simpler ingredient names (e.g., "chicken breast" instead of "organic free-range chicken")
- Use generic terms rather than brand names

**"Recipe generation failed"**
- Check your Groq API key is valid and has remaining quota
- Ensure internet connection is stable

### Support

If you encounter issues:

1. Check the [troubleshooting section](#troubleshooting)
2. Search existing [GitHub issues](https://github.com/yourusername/ai-recipe-app/issues)
3. Create a new issue with detailed error description

## 🙏 Acknowledgments

- [Groq](https://groq.com/) for providing fast AI inference
- [USDA FoodData Central](https://fdc.nal.usda.gov/) for comprehensive nutritional data
- [Streamlit](https://streamlit.io/) for the amazing web app framework
- The open-source community for inspiration and tools

---

**Made with ❤️ for healthy cooking and smart nutrition**

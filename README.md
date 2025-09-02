# 🥗 NutrifyAI - AI-Powered Healthy Recipe & Macro Calculator

A sophisticated Streamlit web application that generates personalized healthy recipes from available ingredients and provides detailed nutritional analysis. Built with advanced AI, modern UI design, and comprehensive recipe management features.

![Python](https://img.shields.io/badge/python-v3.7+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-latest-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![AI](https://img.shields.io/badge/AI-Llama--3.1--8B--Instant-purple.svg)

## ✨ Key Features

### 🤖 **AI-Powered Recipe Generation**
- **Advanced AI Model**: Uses Groq's Llama-3.1-8B-Instant for intelligent recipe creation
- **Structured Output**: Pydantic validation ensures consistent, high-quality recipe data
- **Ingredient-Only Recipes**: Creates recipes using ONLY the ingredients you provide
- **Smart Prompting**: Optimized prompts for culinary realism and nutritional balance

### 📊 **Comprehensive Nutritional Analysis**
- **USDA Integration**: Fetches accurate macro data from 200,000+ verified food items
- **Detailed Breakdown**: Protein, carbs, fat, fiber, and calories per ingredient
- **Per-Serving & Total Macros**: Complete nutritional analysis for meal planning
- **Real-time Calculations**: Instant macro scaling based on ingredient quantities

### 🎨 **Modern User Experience**
- **Glassmorphism Design**: Beautiful, modern UI with advanced CSS animations
- **Responsive Layout**: Optimized for desktop, tablet, and mobile devices
- **Interactive Elements**: Hover effects, smooth transitions, and visual feedback
- **Intuitive Navigation**: Clean, organized interface with helpful tooltips

### 🗄️ **Advanced Recipe Management**
- **SQLite Database**: Persistent storage with comprehensive recipe metadata
- **Smart Filtering**: Filter by dietary restrictions, cuisine, meal type, cooking time, and difficulty
- **Search Functionality**: Find recipes by title or ingredients
- **Rating System**: 5-star rating system with real-time statistics
- **Favorites Management**: Save and organize your preferred recipes

### 🔍 **Quality Assurance & Analytics**
- **Recipe Quality Scoring**: Automatic validation with helpful feedback
- **Ingredient Usage Verification**: Ensures all provided ingredients are used
- **Spelling Suggestions**: Intelligent error detection with correction tips
- **Success Rate Tracking**: Monitor recipe generation performance
- **User Statistics**: Track total recipes, favorites, and average ratings

### ⚡ **Performance & Reliability**
- **Fast AI Inference**: Leverages Groq's ultra-fast hardware for quick responses
- **Error Handling**: Graceful fallbacks and user-friendly error messages
- **Caching System**: Optimized database connections for better performance
- **Free APIs**: Cost-effective operation using generous free tiers

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- Free API keys from Groq and USDA

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/shaunn17/NutrifyAI.git
   cd NutrifyAI
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

## 📖 Usage Guide

### Basic Recipe Generation

1. **Enter Ingredients**: Type your available ingredients separated by commas
   ```
   chicken breast, quinoa, spinach, olive oil, garlic
   ```

2. **Generate Recipe**: Click "🚀 Create My Recipe" to get your AI-created recipe

3. **Review Results**: 
   - Complete recipe with cooking instructions
   - Ingredient quantities in grams
   - Detailed macro breakdown per ingredient
   - Per-serving and total nutrition information

### Advanced Features

#### 🎲 **Surprise Me Button**
- Generates random ingredient combinations for inspiration
- Perfect for discovering new recipe ideas

#### 🔍 **Recipe Filtering & Discovery**
Filter your saved recipes by:
- **🥗 Dietary Restrictions**: None, Vegetarian, Vegan, Keto, Paleo
- **🌍 Cuisine Types**: Italian, Asian, Mexican, Mediterranean, American, Indian, French, Thai
- **🍽️ Meal Types**: Breakfast, Lunch, Dinner, Snacks, Desserts
- **⏱️ Cooking Time**: Quick (15min), Medium (30min), Long (60min+)
- **📚 Difficulty Level**: Beginner, Intermediate, Advanced

#### 📚 **Recipe Management**
- **Recipe History**: Browse all your generated recipes
- **Favorites**: Save and organize your preferred recipes
- **Search**: Find recipes by title or ingredients
- **Rating System**: Rate recipes 1-5 stars
- **Statistics**: Track your recipe generation success

#### 🗑️ **Data Management**
- **Individual Deletion**: Remove specific recipes
- **Bulk Operations**: Clear all recipes with confirmation
- **Data Export**: All data stored in local SQLite database

### Example Input/Output

**Input:**
```
salmon, sweet potato, broccoli, olive oil, lemon
```

**Output:**
- **Recipe**: "Roasted Salmon with Sweet Potato and Broccoli" (4 servings)
- **Macros per serving**: ~35g protein, 25g carbs, 12g fat, 6g fiber
- **Cooking steps**: Detailed preparation and cooking instructions
- **Quality Score**: 95/100 with validation feedback

## 🏗️ Technical Architecture

```
NutrifyAI/
├── app.py              # Main Streamlit application (1,700+ lines)
├── database.py         # SQLite database management (535 lines)
├── utils.py            # USDA API integration (122 lines)
├── requirements.txt    # Python dependencies
├── recipes.db          # SQLite database file
└── .streamlit/
    └── secrets.toml    # API keys configuration
```

### Key Components

- **`app.py`**: Main application with Streamlit UI, AI integration, and comprehensive recipe management
- **`database.py`**: SQLite database with advanced filtering, search, and analytics capabilities
- **`utils.py`**: USDA FoodData Central API wrapper with macro calculation algorithms
- **Pydantic Models**: Structured data validation ensuring recipe quality and consistency
- **Advanced CSS**: Custom glassmorphism design with animations and responsive layout

## 🔌 API Integrations

### Groq API
- **Model**: Llama-3.1-8B-Instant
- **Purpose**: AI-powered recipe generation
- **Performance**: 500+ tokens/second generation speed
- **Rate Limit**: Generous free tier
- **Documentation**: [console.groq.com](https://console.groq.com)

### USDA FoodData Central
- **Purpose**: Nutritional data lookup and macro calculations
- **Coverage**: 200,000+ verified food items
- **Rate Limit**: 1,000 requests/hour (free)
- **Accuracy**: Government-verified nutritional data
- **Documentation**: [fdc.nal.usda.gov](https://fdc.nal.usda.gov/api-guide.html)

## 🧪 Technical Implementation

### Recipe Generation Pipeline

1. **Input Validation**: Parses and validates ingredient list
2. **AI Prompt Engineering**: Constructs optimized prompts for Groq AI
3. **JSON Parsing**: Extracts and validates recipe JSON with Pydantic
4. **Quality Validation**: Checks ingredient usage and recipe quality
5. **Macro Calculation**: Queries USDA API for each ingredient
6. **Data Scaling**: Calculates per-serving and total macros
7. **Database Storage**: Saves recipe with metadata and analytics

### Data Flow

```mermaid
graph LR
    A[User Input] --> B[Input Validation]
    B --> C[Groq AI]
    C --> D[JSON Validation]
    D --> E[Quality Check]
    E --> F[USDA API]
    F --> G[Macro Calculation]
    G --> H[Database Storage]
    H --> I[UI Display]
```

### Quality Assurance System

- **Ingredient Usage Verification**: Ensures all provided ingredients are used
- **Spelling Detection**: Identifies common spelling errors with suggestions
- **Serving Size Validation**: Checks for realistic portion sizes
- **Recipe Completeness**: Validates cooking instructions and steps
- **Quality Scoring**: Provides 0-100 quality score with detailed feedback

## 🎯 Performance Optimizations

- **Database Caching**: Optimized SQLite connections with intelligent caching
- **API Rate Limiting**: Efficient API usage with error handling
- **UI Responsiveness**: Smooth animations and fast page loads
- **Memory Management**: Efficient data structures and cleanup
- **Error Recovery**: Graceful handling of API failures and edge cases

## 🔧 Configuration Options

### Environment Variables (Alternative)
```bash
export GROQ_API_KEY="your_groq_api_key_here"
export USDA_API_KEY="your_usda_api_key_here"
```

### Deployment
For deployment on Streamlit Cloud or other platforms:
- `groq_api_key`: Your Groq API key
- `usda_api_key`: Your USDA API key

## 🆘 Troubleshooting

### Common Issues

**"Please add your API keys in Secrets"**
- Ensure your `secrets.toml` file is in the `.streamlit/` directory
- Verify API keys are correctly formatted (no extra spaces/quotes)

**"No USDA match found"**
- Try simpler ingredient names (e.g., "chicken breast" instead of "organic free-range chicken")
- Use generic terms rather than brand names
- Check spelling of ingredient names

**"Recipe generation failed"**
- Check your Groq API key is valid and has remaining quota
- Ensure internet connection is stable
- Try with fewer ingredients (4-8 ingredients work best)

**"Ingredients not used in recipe"**
- Check spelling (e.g., "broccoli" not "brocoli")
- Use simpler ingredient names
- Try regenerating the recipe

## 🔮 Future Enhancements

- [x] Recipe rating and favorites system ✅
- [x] Advanced filtering and search ✅
- [x] Quality validation and feedback ✅
- [x] Modern glassmorphism UI ✅
- [x] Recipe management and analytics ✅
- [ ] Shopping list generation
- [ ] Recipe image generation
- [ ] Meal planning calendar
- [ ] Export to PDF/email
- [ ] Ingredient substitution suggestions
- [ ] Calorie target optimization
- [ ] Multi-language support
- [ ] Recipe sharing and collaboration

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


*Transform any combination of ingredients into a delicious, healthy meal with AI precision!*
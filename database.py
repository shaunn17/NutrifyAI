import sqlite3
import json
import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import uuid

@dataclass
class Recipe:
    id: str
    title: str
    servings: int
    ingredients: List[Dict[str, float]]  # [{"name": str, "grams": float}]
    steps: List[str]
    nutrition_per_recipe: Dict[str, float]
    nutrition_per_serving: Dict[str, float]
    created_at: str
    rating: Optional[int] = None
    is_favorite: bool = False
    tags: List[str] = None

class RecipeDatabase:
    def __init__(self, db_path: str = "recipes.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create recipes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                servings INTEGER NOT NULL,
                ingredients TEXT NOT NULL,  -- JSON string
                steps TEXT NOT NULL,        -- JSON string
                nutrition_per_recipe TEXT NOT NULL,  -- JSON string
                nutrition_per_serving TEXT NOT NULL, -- JSON string
                created_at TEXT NOT NULL,
                rating INTEGER,
                is_favorite BOOLEAN DEFAULT FALSE,
                tags TEXT  -- JSON string
            )
        ''')
        
        # Create recipe_history table for tracking generation attempts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipe_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_ingredients TEXT NOT NULL,
                recipe_id TEXT,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        ''')
        
        # Create user_preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preference_key TEXT UNIQUE NOT NULL,
                preference_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_recipe(self, title: str, servings: int, ingredients: List[Dict], 
                   steps: List[str], nutrition_per_recipe: Dict[str, float], 
                   nutrition_per_serving: Dict[str, float], tags: List[str] = None) -> str:
        """Save a recipe to the database and return the recipe ID."""
        recipe_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO recipes (
                id, title, servings, ingredients, steps, 
                nutrition_per_recipe, nutrition_per_serving, 
                created_at, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            recipe_id,
            title,
            servings,
            json.dumps(ingredients),
            json.dumps(steps),
            json.dumps(nutrition_per_recipe),
            json.dumps(nutrition_per_serving),
            created_at,
            json.dumps(tags or [])
        ))
        
        conn.commit()
        conn.close()
        
        return recipe_id
    
    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Retrieve a recipe by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
        
        return Recipe(
            id=row[0],
            title=row[1],
            servings=row[2],
            ingredients=json.loads(row[3]),
            steps=json.loads(row[4]),
            nutrition_per_recipe=json.loads(row[5]),
            nutrition_per_serving=json.loads(row[6]),
            created_at=row[7],
            rating=row[8],
            is_favorite=bool(row[9]),
            tags=json.loads(row[10]) if row[10] else []
        )
    
    def get_all_recipes(self, limit: int = 50, offset: int = 0) -> List[Recipe]:
        """Get all recipes with pagination."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM recipes 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        recipes = []
        for row in rows:
            recipes.append(Recipe(
                id=row[0],
                title=row[1],
                servings=row[2],
                ingredients=json.loads(row[3]),
                steps=json.loads(row[4]),
                nutrition_per_recipe=json.loads(row[5]),
                nutrition_per_serving=json.loads(row[6]),
                created_at=row[7],
                rating=row[8],
                is_favorite=bool(row[9]),
                tags=json.loads(row[10]) if row[10] else []
            ))
        
        return recipes
    
    def search_recipes(self, query: str, limit: int = 20) -> List[Recipe]:
        """Search recipes by title or ingredients."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM recipes 
            WHERE title LIKE ? OR ingredients LIKE ?
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        recipes = []
        for row in rows:
            recipes.append(Recipe(
                id=row[0],
                title=row[1],
                servings=row[2],
                ingredients=json.loads(row[3]),
                steps=json.loads(row[4]),
                nutrition_per_recipe=json.loads(row[5]),
                nutrition_per_serving=json.loads(row[6]),
                created_at=row[7],
                rating=row[8],
                is_favorite=bool(row[9]),
                tags=json.loads(row[10]) if row[10] else []
            ))
        
        return recipes
    
    def update_recipe_rating(self, recipe_id: str, rating: int) -> bool:
        """Update the rating for a recipe."""
        if rating < 1 or rating > 5:
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE recipes SET rating = ? WHERE id = ?
        ''', (rating, recipe_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def toggle_favorite(self, recipe_id: str) -> bool:
        """Toggle the favorite status of a recipe."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current favorite status
        cursor.execute('SELECT is_favorite FROM recipes WHERE id = ?', (recipe_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False
        
        new_status = not bool(row[0])
        cursor.execute('''
            UPDATE recipes SET is_favorite = ? WHERE id = ?
        ''', (new_status, recipe_id))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_favorites(self) -> List[Recipe]:
        """Get all favorite recipes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM recipes 
            WHERE is_favorite = TRUE 
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        recipes = []
        for row in rows:
            recipes.append(Recipe(
                id=row[0],
                title=row[1],
                servings=row[2],
                ingredients=json.loads(row[3]),
                steps=json.loads(row[4]),
                nutrition_per_recipe=json.loads(row[5]),
                nutrition_per_serving=json.loads(row[6]),
                created_at=row[7],
                rating=row[8],
                is_favorite=bool(row[9]),
                tags=json.loads(row[10]) if row[10] else []
            ))
        
        return recipes
    
    def log_recipe_generation(self, input_ingredients: str, recipe_id: str = None, 
                            success: bool = True, error_message: str = None):
        """Log a recipe generation attempt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO recipe_history (
                input_ingredients, recipe_id, success, error_message, created_at
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            input_ingredients,
            recipe_id,
            success,
            error_message,
            datetime.datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_recipe_stats(self) -> Dict[str, any]:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total recipes
        cursor.execute('SELECT COUNT(*) FROM recipes')
        total_recipes = cursor.fetchone()[0]
        
        # Favorite recipes
        cursor.execute('SELECT COUNT(*) FROM recipes WHERE is_favorite = TRUE')
        favorite_recipes = cursor.fetchone()[0]
        
        # Average rating
        cursor.execute('SELECT AVG(rating) FROM recipes WHERE rating IS NOT NULL')
        avg_rating = cursor.fetchone()[0] or 0
        
        # Total generation attempts
        cursor.execute('SELECT COUNT(*) FROM recipe_history')
        total_attempts = cursor.fetchone()[0]
        
        # Success rate
        cursor.execute('SELECT COUNT(*) FROM recipe_history WHERE success = TRUE')
        successful_attempts = cursor.fetchone()[0]
        
        success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0
        
        conn.close()
        
        return {
            'total_recipes': total_recipes,
            'favorite_recipes': favorite_recipes,
            'average_rating': round(avg_rating, 2),
            'total_attempts': total_attempts,
            'success_rate': round(success_rate, 2)
        }
    
    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete a recipe from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM recipes WHERE id = ?', (recipe_id,))
        success = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return success

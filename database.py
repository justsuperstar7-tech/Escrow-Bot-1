import sqlite3
import json
from datetime import datetime
from config import DATABASE_PATH

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        """Create all necessary tables."""
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                rank TEXT DEFAULT '#N/A',
                active_deals INTEGER DEFAULT 0,
                total_escrows INTEGER DEFAULT 0,
                volume_ton REAL DEFAULT 0,
                volume_usdt REAL DEFAULT 0,
                volume_inr REAL DEFAULT 0,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Deals table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                deal_id TEXT UNIQUE,
                amount REAL,
                currency TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Co-admins table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS co_admins (
                user_id TEXT PRIMARY KEY,
                added_by TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Global stats table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_stats (
                id INTEGER PRIMARY KEY,
                total_deals INTEGER DEFAULT 0,
                total_volume_ton REAL DEFAULT 0,
                total_volume_usdt REAL DEFAULT 0,
                total_volume_inr REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default global stats if not exists
        self.cursor.execute('SELECT COUNT(*) FROM global_stats')
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute('''
                INSERT INTO global_stats (total_deals, total_volume_ton, total_volume_usdt, total_volume_inr)
                VALUES (0, 0, 0, 0)
            ''')
        
        self.conn.commit()
    
    def register_user(self, user_id, username):
        """Register a new user."""
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username)
            VALUES (?, ?)
        ''', (user_id, username))
        self.conn.commit()
    
    def get_user_stats(self, user_id):
        """Get user statistics."""
        self.cursor.execute('''
            SELECT * FROM users WHERE user_id = ?
        ''', (user_id,))
        row = self.cursor.fetchone()
        
        if row:
            return {
                'username': row[1],
                'rank': row[2],
                'active_deals': row[3],
                'total_escrows': row[4],
                'volume_ton': row[5],
                'volume_usdt': row[6],
                'volume_inr': row[7]
            }
        return None
    
    def get_user_deals(self, user_id):
        """Get user deals."""
        self.cursor.execute('''
            SELECT * FROM deals WHERE user_id = ? ORDER BY created_at DESC LIMIT 10
        ''', (user_id,))
        rows = self.cursor.fetchall()
        
        deals = []
        for row in rows:
            deals.append({
                'id': row[2],
                'amount': row[3],
                'currency': row[4],
                'status': row[5]
            })
        return deals
    
    def get_pending_deals(self, user_id):
        """Get pending deals for user."""
        self.cursor.execute('''
            SELECT * FROM deals WHERE user_id = ? AND status = 'pending'
        ''', (user_id,))
        rows = self.cursor.fetchall()
        
        pending = []
        for row in rows:
            pending.append({
                'id': row[2],
                'amount': row[3],
                'currency': row[4],
                'status': row[5]
            })
        return pending
    
    def get_global_stats(self):
        """Get global statistics."""
        self.cursor.execute('SELECT * FROM global_stats WHERE id = 1')
        row = self.cursor.fetchone()
        
        if row:
            return {
                'total_deals': row[1],
                'total_volume_ton': row[2],
                'total_volume_usdt': row[3],
                'total_volume_inr': row[4]
            }
        return {'total_deals': 0, 'total_volume_ton': 0, 'total_volume_usdt': 0, 'total_volume_inr': 0}
    
    def update_global_stats(self, deals=None, volume_ton=None, volume_usdt=None, volume_inr=None):
        """Update global statistics."""
        current = self.get_global_stats()
        
        total_deals = deals if deals is not None else current['total_deals']
        total_volume_ton = volume_ton if volume_ton is not None else current['total_volume_ton']
        total_volume_usdt = volume_usdt if volume_usdt is not None else current['total_volume_usdt']
        total_volume_inr = volume_inr if volume_inr is not None else current['total_volume_inr']
        
        self.cursor.execute('''
            UPDATE global_stats 
            SET total_deals = ?, total_volume_ton = ?, total_volume_usdt = ?, total_volume_inr = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        ''', (total_deals, total_volume_ton, total_volume_usdt, total_volume_inr))
        self.conn.commit()
    
    def is_co_admin(self, user_id):
        """Check if user is a co-admin."""
        self.cursor.execute('SELECT 1 FROM co_admins WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone() is not None
    
    def add_co_admin(self, user_id, added_by):
        """Add a co-admin."""
        try:
            self.cursor.execute('''
                INSERT INTO co_admins (user_id, added_by)
                VALUES (?, ?)
            ''', (user_id, added_by))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def remove_co_admin(self, user_id):
        """Remove a co-admin."""
        self.cursor.execute('DELETE FROM co_admins WHERE user_id = ?', (user_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_all_co_admins(self):
        """Get all co-admins."""
        self.cursor.execute('''
            SELECT user_id, added_by, added_at FROM co_admins
        ''')
        rows = self.cursor.fetchall()
        return [{'user_id': row[0], 'added_by': row[1], 'added_at': row[2]} for row in rows]
    
    def get_all_users(self):
        """Get all users."""
        self.cursor.execute('SELECT user_id FROM users')
        return [row[0] for row in self.cursor.fetchall()]
    
    def update_user_stats(self, user_id, stats):
        """Update user statistics."""
        self.cursor.execute('''
            UPDATE users 
            SET rank = ?, active_deals = ?, total_escrows = ?, 
                volume_ton = ?, volume_usdt = ?, volume_inr = ?
            WHERE user_id = ?
        ''', (stats.get('rank', '#N/A'), stats.get('active_deals', 0),
              stats.get('total_escrows', 0), stats.get('volume_ton', 0),
              stats.get('volume_usdt', 0), stats.get('volume_inr', 0), user_id))
        self.conn.commit()
    
    def add_deal(self, user_id, deal_id, amount, currency):
        """Add a new deal."""
        self.cursor.execute('''
            INSERT INTO deals (user_id, deal_id, amount, currency)
            VALUES (?, ?, ?, ?)
        ''', (user_id, deal_id, amount, currency))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def close(self):
        """Close database connection."""
        self.conn.close()

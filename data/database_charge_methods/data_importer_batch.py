from neo4j import GraphDatabase
import pandas as pd
import os

class OptimizedMovieLensImporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def bulk_import_movies(self, movies_path):
        movies_df = pd.read_csv(movies_path)
        
        with self.driver.session() as session:
            # Crear índice
            session.run("CREATE INDEX movie_id_index IF NOT EXISTS FOR (m:Movie) ON (m.movieId)")
            
            # Importación por lotes
            batch_size = 1000
            for i in range(0, len(movies_df), batch_size):
                batch = movies_df.iloc[i:i+batch_size]
                
                with session.begin_transaction() as tx:
                    for _, movie in batch.iterrows():
                        genres = '|'.join(movie['genres']) if isinstance(movie['genres'], list) else movie['genres']
                        
                        tx.run("""
                        MERGE (m:Movie {movieId: $movieId})
                        SET 
                            m.title = $title, 
                            m.genres = $genres,
                            m.total_ratings = $total_ratings,
                            m.avg_rating = $avg_rating,
                            m.total_users = $total_users,
                            m.popularity_score = $popularity_score
                        """, {
                            'movieId': movie['movieId'],
                            'title': movie['title'],
                            'genres': genres,
                            'total_ratings': movie.get('total_ratings', 0),
                            'avg_rating': movie.get('avg_rating', 0),
                            'total_users': movie.get('total_users', 0),
                            'popularity_score': movie.get('popularity_score', 0)
                        })
                
                print(f"Procesados {i+batch_size} películas...")
    
    def bulk_import_ratings(self, ratings_path):
        ratings_df = pd.read_csv(ratings_path)
        
        with self.driver.session() as session:
            # Crear índices
            session.run("CREATE INDEX user_id_index IF NOT EXISTS FOR (u:User) ON (u.userId)")
            
            # Importación por lotes
            batch_size = 5000
            for i in range(0, len(ratings_df), batch_size):
                batch = ratings_df.iloc[i:i+batch_size]
                
                with session.begin_transaction() as tx:
                    for _, rating in batch.iterrows():
                        tx.run("""
                        MERGE (u:User {userId: $userId})
                        MERGE (m:Movie {movieId: $movieId})
                        MERGE (u)-[r:RATED]->(m)
                        SET 
                            r.rating = $rating, 
                            r.timestamp = $timestamp
                        """, {
                            'userId': rating['userId'],
                            'movieId': rating['movieId'],
                            'rating': rating['rating'],
                            'timestamp': rating['timestamp']
                        })
                
                print(f"Procesados {i+batch_size} ratings...")
    def bulk_import_tags(self, tags_path):
        tags_df = pd.read_csv(tags_path)
        
    
    # Filtrar filas con NaN en la columna 'tag'
        tags_df = tags_df.dropna(subset=['tag'])
        with self.driver.session() as session:
            # Crear índices para tags y usuarios
            session.run("CREATE INDEX tag_name_index IF NOT EXISTS FOR (t:Tag) ON (t.name)")
            session.run("CREATE INDEX user_id_index IF NOT EXISTS FOR (u:User) ON (u.userId)")

            # Importación por lotes
            batch_size = 5000
            for i in range(0, len(tags_df), batch_size):
                batch = tags_df.iloc[i:i+batch_size]
                
                with session.begin_transaction() as tx:
                    for _, tag in batch.iterrows():
                        tx.run("""
                        MERGE (u:User {userId: $userId})
                        MERGE (m:Movie {movieId: $movieId})
                        MERGE (t:Tag {name: $tagName})
                        MERGE (u)-[:TAGGED {timestamp: $timestamp}]->(m)
                        MERGE (m)-[:HAS_TAG]->(t)
                        """, {
                            'userId': tag['userId'],
                            'movieId': tag['movieId'],
                            'tagName': tag['tag'],
                            'timestamp': tag['timestamp']
                        })
                
                print(f"Procesados {i+batch_size} tags...")

    def bulk_import_genome_scores(self, genome_scores_path):
        genome_scores_df = pd.read_csv(genome_scores_path)
        
        with self.driver.session() as session:
            # Crear índice para tags
            session.run("CREATE INDEX tag_name_index IF NOT EXISTS FOR (t:Tag) ON (t.name)")

            # Importación por lotes
            batch_size = 5000
            for i in range(0, len(genome_scores_df), batch_size):
                batch = genome_scores_df.iloc[i:i+batch_size]
                
                with session.begin_transaction() as tx:
                    for _, score in batch.iterrows():
                        tx.run("""
                        MERGE (m:Movie {movieId: $movieId})
                        MERGE (t:Tag {tagId: $tagId})
                        MERGE (m)-[r:HAS_TAG]->(t)
                        SET r.relevance = $relevance
                        """, {
                            'movieId': score['movieId'],
                            'tagId': score['tagId'],
                            'relevance': score['relevance']
                        })
                
                print(f"Procesados {i+batch_size} relevancias de tags...")

def main():
    # Configuración de conexión
    URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    USER =  os.getenv('NEO4J_USER', 'neo4j')
    PASSWORD = os.getenv('NEO4J_PASSWORD')
    
    # Rutas de archivos
    DATASET_PATH = 'data/movielens/processed'
    DATASET_PATH2= 'data/movielens'
    MOVIES_PATH = os.path.join(DATASET_PATH, 'movies_processed.csv')
    RATINGS_PATH = os.path.join(DATASET_PATH, 'ratings_processed.csv')
    TAGS_PATH = os.path.join(DATASET_PATH2, 'tag.csv')
    GENOME_SCORES_PATH = os.path.join(DATASET_PATH2, 'genome_scores.csv')
    
    importer = OptimizedMovieLensImporter(URI, USER, PASSWORD)
    
    try:
        importer.bulk_import_movies(MOVIES_PATH)
        importer.bulk_import_ratings(RATINGS_PATH)
        importer.bulk_import_tags(TAGS_PATH)
        importer.bulk_import_genome_scores(GENOME_SCORES_PATH)
        print("Importación completada!")
    
    finally:
        importer.driver.close()

if __name__ == '__main__':
    main()
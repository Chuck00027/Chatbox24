CREATE DATABASE knowledge_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE knowledge_db;

CREATE TABLE knowledge_base (
    id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT NOT NULL,
    source_type ENUM('PDF', 'Manual', 'Email') NOT NULL, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB 
DEFAULT CHARSET=utf8mb4;
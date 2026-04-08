-- ==================== Friendship Tables ====================

-- Create friend_requests table
CREATE TABLE IF NOT EXISTS friend_requests (
    id VARCHAR(36) PRIMARY KEY,
    from_user_id VARCHAR(36) NOT NULL,
    to_user_id VARCHAR(36) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending' COMMENT 'pending, accepted, rejected, canceled',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (from_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (to_user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    INDEX idx_from_user_id (from_user_id),
    INDEX idx_to_user_id (to_user_id),
    INDEX idx_status (status),
    UNIQUE KEY unique_pending_request (from_user_id, to_user_id, status) COMMENT 'One pending request per pair'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create friendships table (for accepted friendships only)
CREATE TABLE IF NOT EXISTS friendships (
    id VARCHAR(36) PRIMARY KEY,
    user_id_1 VARCHAR(36) NOT NULL COMMENT 'Smaller UUID (alphabetically)',
    user_id_2 VARCHAR(36) NOT NULL COMMENT 'Larger UUID (alphabetically)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id_1) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id_2) REFERENCES users(id) ON DELETE CASCADE,
    
    INDEX idx_user_id_1 (user_id_1),
    INDEX idx_user_id_2 (user_id_2),
    UNIQUE KEY unique_friendship (user_id_1, user_id_2) COMMENT 'Prevent duplicate friendships'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add comment to database
ALTER TABLE friend_requests COMMENT='Stores friend requests with workflow: pending -> accepted/rejected/canceled';
ALTER TABLE friendships COMMENT='Stores accepted friendships with deduplication (user_id_1 < user_id_2)';

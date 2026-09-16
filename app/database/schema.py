"""Database DDL definitions, indexing, and analytical views."""

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id TEXT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    response_time_hrs REAL NOT NULL,
    resolution_time_hrs REAL,
    agent_id TEXT NOT NULL,
    customer_rating INTEGER,
    issue_summary TEXT NOT NULL
);
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets (status);",
    "CREATE INDEX IF NOT EXISTS idx_tickets_priority ON support_tickets (priority);",
    "CREATE INDEX IF NOT EXISTS idx_tickets_category ON support_tickets (category);",
    "CREATE INDEX IF NOT EXISTS idx_tickets_agent ON support_tickets (agent_id);",
    "CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON support_tickets (created_at);",
    "CREATE INDEX IF NOT EXISTS idx_tickets_status_priority ON support_tickets (status, priority);"
]

CREATE_VIEWS_SQL = [
    """
    CREATE VIEW IF NOT EXISTS v_agent_performance AS
    SELECT 
        agent_id,
        COUNT(*) AS total_assigned,
        SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS tickets_resolved,
        ROUND(AVG(CASE WHEN status = 'Resolved' THEN resolution_time_hrs END), 2) AS avg_resolution_time_hrs,
        ROUND(AVG(response_time_hrs), 2) AS avg_response_time_hrs,
        ROUND(AVG(customer_rating), 2) AS avg_customer_rating
    FROM support_tickets
    GROUP BY agent_id;
    """,
    """
    CREATE VIEW IF NOT EXISTS v_category_summary AS
    SELECT 
        category,
        COUNT(*) AS total_tickets,
        SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) AS open_tickets,
        SUM(CASE WHEN status = 'Escalated' THEN 1 ELSE 0 END) AS escalated_tickets,
        SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved_tickets,
        ROUND(AVG(resolution_time_hrs), 2) AS avg_resolution_time_hrs,
        ROUND(AVG(customer_rating), 2) AS avg_customer_rating
    FROM support_tickets
    GROUP BY category;
    """
]

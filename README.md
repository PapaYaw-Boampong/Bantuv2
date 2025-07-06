# Backend Documentation

## Overview

This backend system powers a language challenge platform where users can participate in transcription, translation, and annotation tasks. It leverages a reward mechanism to incentivize contributions and implements a sophisticated evaluation system to ensure quality.

## Table of Contents

- [Setup and Installation](#setup-and-installation)
- [Architecture](#architecture)
- [Core Components](#core-components)
- [API Endpoints](#api-endpoints)
- [Database Models](#database-models)
- [Services](#services)
- [Reward System](#reward-system)
- [Evaluation System](#evaluation-system)
- [Troubleshooting](#troubleshooting)
- [Development Guidelines](#development-guidelines)

## Setup and Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis (optional, for caching)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the server**
   ```bash
   uvicorn main:app --reload
   ```

7. **Access the API documentation**
   
   Open your browser and navigate to: `http://localhost:8000/docs`

## Architecture

The application follows a layered architecture:

- **API Layer**: FastAPI routes and controllers
- **Service Layer**: Business logic and processing
- **CRUD Layer**: Database operations
- **Model Layer**: Database models and schemas

## Core Components

### Challenge System
Manages competitions and bounties where users contribute language content.

### User Management
Handles user registration, authentication, and profile management.

### Contribution System
Processes user submissions for transcription, translation, and annotation tasks.

### Evaluation System
Multi-branch assessment of contributions to ensure quality and validate submissions.

### Reward System
Distributes rewards (cash, badges, swag) to users based on their performance.

## API Endpoints

### Authentication
- `POST /auth/login`: User login
- `POST /auth/register`: User registration
- `POST /auth/refresh-token`: Refresh authentication token

### Challenges
- `GET /challenges`: List challenges
- `GET /challenges/{challenge_id}`: Get challenge details
- `POST /challenges`: Create a new challenge
- `PUT /challenges/{challenge_id}`: Update challenge
- `DELETE /challenges/{challenge_id}`: Delete challenge

### Contributions
- `POST /contributions/{type}`: Submit contribution
- `GET /contributions/user/{user_id}`: Get user contributions
- `GET /contributions/challenge/{challenge_id}`: Get challenge contributions

### Rewards
- `GET /rewards`: List rewards
- `POST /rewards/milestone`: Create milestone reward
- `POST /rewards/challenge`: Create challenge reward
- `POST /rewards/award`: Award reward to user

### Evaluations
- `GET /evaluations/tasks`: Get evaluation tasks
- `POST /evaluations/submit`: Submit evaluation
- `GET /evaluations/{evaluation_id}`: Get evaluation details

## Database Models

### Challenge Models
- `Challenge`: Core challenge entity
- `ChallengeParticipation`: User participation in challenges
- `ChallengeRule`: Rules associated with challenges

### Reward Models
- `Milestone`: Achievement-based rewards
- `UserMilestone`: User milestone achievements
- `ChallengeReward`: Rewards associated with challenges
- `UserChallengeReward`: Rewards awarded to users

### Contribution Models
- `TranslationContribution`
- `AnnotationContribution`
- `TranscriptionContribution`

### Evaluation Models
- `EvaluationInstance`
- `EvaluationBranch`
- `EvaluationStep`

## Services

The application implements a dual-layer service architecture:

### CRUD Layer
Handles direct database operations without business logic:

```python
# Example usage
reward_crud = RewardsCRUD(db)
reward = await reward_crud.get_challenge_reward(reward_id)
```

### Service Layer
Implements business logic and validation:

```python
# Example usage
reward_service = RewardsService(db)
result = await reward_service.award_milestone(user_milestone_data)
```

## Reward System

The platform supports multiple reward types:

### Cash Rewards
```json
{
  "amount": 100,
  "currency": "USD"
}
```

### Badge Rewards
```json
{
  "badge_name": "Top Contributor",
  "badge_description": "Awarded for top contributions.",
  "badge_icon": "url_to_icon"
}
```

### Swag Rewards
```json
{
  "swag_item": "T-shirt",
  "swag_description": "Exclusive challenge t-shirt",
  "token": "swag_token"
}
```

### Distribution Types

- **Fixed**: All winners get the same reward
- **Tiered**: Different rewards based on ranking

Example tiered reward:
```json
{
  "reward_distribution_type": "tiered",
  "reward_value": {
    "tier_1": {
      "rank": 1,
      "cash": {
        "amount": 150,
        "currency": "USD"
      }
    },
    "tier_2": {
      "rank": 2,
      "cash": {
        "amount": 100,
        "currency": "USD"
      }
    }
  }
}
```

## Evaluation System

The evaluation system implements a multi-branch approach:

1. Each contribution gets assigned to multiple evaluators
2. Evaluations follow a tree structure with multiple branches
3. Steps in the evaluation process can be assigned based on user proficiency

```python
# Example: Assigning evaluation steps
steps = await evaluation_service.assign_evaluation_step_to_user(
    user_id=user_id,
    proficiency_level=3,
    contribution_type="translation",
    num_steps=2
)
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check PostgreSQL is running
   - Verify database credentials in `.env` file

2. **Authentication Problems**
   - Ensure JWT secret is properly set
   - Check token expiration settings

3. **Missing Dependencies**
   - Run `pip install -r requirements.txt` to ensure all packages are installed

### Logging

The application uses structured logging for monitoring:

```
YYYY-MM-DD HH:MM:SS - service_name - LEVEL - Message
```

Log files:
- `app.log`: Main application logs
- `rewards_service.log`: Reward-specific operations
- `evaluation_service.log`: Evaluation-specific operations

### Database Troubleshooting

To reset the database if needed:
```bash
# Drop and recreate database
alembic downgrade base
alembic upgrade head
```

For database inspection, use:
```bash
# Run SQL directly (adjust for your DB setup)
python -c "from core.db import engine; result = engine.execute('SELECT * FROM challenge LIMIT 5'); print(result.fetchall())"
```

## Development Guidelines

1. Always create CRUD and Service classes for new features
2. Implement proper validation in service layer
3. Use logging for important operations
4. Maintain separation between database operations and business logic
5. Follow SQLModel/SQLAlchemy best practices for database operations

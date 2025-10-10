# BotCamp Medical - Telegram Bot

Telegram quiz bot for MBChB students, with AI question uploads and admin features.

A comprehensive Telegram bot for medical students to practice quizzes and improve their knowledge through interactive learning.

## Features

- 🏥 **Medical Quiz System**: Interactive multiple-choice questions
- 🎓 **University & Course Selection**: Support for multiple universities and medical courses
- 📚 **Topic-based Learning**: Organized by units, topics, and papers
- 📊 **Progress Tracking**: View statistics and performance over time
- 🔧 **Admin Panel**: Manage content and users
- 💾 **SQLite Database**: Lightweight and portable data storage

## Project Structure

```
botcamp-medical/
├── main_sync.py              # Main bot entry point (synchronous version)
├── main.py                   # Main bot entry point (async version - for future use)
├── requirements.txt          # Python dependencies
├── add_sample_data.py        # Script to populate database with sample data
├── handlers/                 # Bot command and callback handlers
│   ├── start_sync.py        # Start command and navigation handlers
│   ├── start.py             # Async version of start handlers
│   ├── quiz.py              # Quiz functionality handlers
│   └── admin.py             # Admin panel handlers
├── database/                 # Database models and configuration
│   ├── models.py            # SQLAlchemy models
│   ├── db.py                # Database connection and setup
│   └── __init__.py
├── utils/                    # Utility functions
│   ├── helpers.py           # Helper functions
│   ├── filters.py           # Message filters
│   └── __init__.py
└── data/                     # Sample data
    └── sample_questions.json # Sample questions and structure
```

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- Telegram Bot Token (from @BotFather)

### 2. Installation

1. Clone or download this project
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Configuration

1. Get your bot token from [@BotFather](https://t.me/BotFather) on Telegram
2. Update the bot token in `main_sync.py`:
   ```python
   BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
   ```

### 4. Database Setup

1. Run the sample data script to create the database and add sample content:
   ```bash
   python add_sample_data.py
   ```

### 5. Running the Bot

Start the bot:
```bash
python main_sync.py
```

The bot will create the database tables automatically and start listening for messages.

## Usage

### For Students

1. **Start the Bot**: Send `/start` to begin
2. **Select University & Course**: Navigate through the menu to select your institution and course
3. **Take Quizzes**: Choose topics and start practicing with multiple-choice questions
4. **View Statistics**: Track your progress and performance

### For Administrators

1. **Admin Access**: Use `/admin` command (requires admin privileges)
2. **Manage Content**: Add universities, courses, units, topics, and questions
3. **View Statistics**: Monitor user activity and system performance

## Bot Commands

- `/start` - Start the bot and show main menu
- `/admin` - Access admin panel (admin users only)

## Database Schema

The bot uses the following main entities:

- **Users**: Telegram users and their information
- **Universities**: Medical universities
- **Courses**: Medical degree programs
- **Units**: Course units/subjects
- **Topics**: Specific topics within units
- **Questions**: Quiz questions with multiple choice answers
- **Quiz Sessions**: User quiz attempts and results
- **Admins**: Bot administrators

## Adding Content

### Adding Questions

You can add questions through the admin panel or by modifying the database directly. Questions include:

- Question text
- Four multiple choice options (A, B, C, D)
- Correct answer
- Explanation
- Difficulty level (easy, medium, hard)
- Associated topic

### Sample Data

The bot comes with sample data including:
- University of Nairobi
- MBChB course
- Anatomy unit
- General Anatomy topic
- 3 sample questions

## Customization

### Adding New Universities

1. Use the admin panel, or
2. Add directly to the database:
   ```python
   university = University(name="Your University Name")
   db.add(university)
   db.commit()
   ```

### Modifying Question Format

Questions follow this structure:
- Multiple choice (A, B, C, D)
- Single correct answer
- Optional explanation
- Difficulty rating

## Troubleshooting

### Common Issues

1. **Bot not responding**: Check if the bot token is correct and the bot is running
2. **Database errors**: Ensure SQLite database file is writable
3. **Import errors**: Verify all dependencies are installed

### Logs

The bot logs all activities to the console. Check the output for error messages and debugging information.

## Future Enhancements

- [ ] Async database operations for better performance
- [ ] More question types (true/false, fill-in-the-blank)
- [ ] Study groups and collaborative features
- [ ] Advanced analytics and reporting
- [ ] Integration with learning management systems
- [ ] Mobile app companion

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

---

**BotCamp Medical** - Empowering medical students through interactive learning! 🏥📚

# Screenshotter

A simple Flask application that provides an API endpoint to capture screenshots of web pages using Firefox in headless mode.

## Features

*   **Screenshot API:** Capture screenshots of any given URL.
*   **Caching:** Caches screenshots to improve performance and reduce redundant captures.
*   **Error Handling:** Robust error handling for invalid URLs, timeouts, and Firefox issues.

## Setup and Installation

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

Before you begin, ensure you have the following installed:

*   Python 3.8+
*   `pip` (Python package installer)
*   `Firefox` browser (must be available in your system's PATH for headless mode)

### Installation Steps

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/screenshotter.git
    cd screenshotter
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Install pre-commit hooks:**

    ```bash
    pip install pre-commit
    pre-commit install
    ```
    This will set up automatic code formatting and linting checks before each commit.

## Running the Application

To start the Flask development server:

```bash
python app.py
```

The application will be running on `http://0.0.0.0:11754`.

## API Usage

### Endpoint

`GET /screenshot`

### Parameters

*   `url` (required): The URL of the webpage to screenshot. Must start with `http://` or `https://`.

### Example

```
http://0.0.0.0:11754/screenshot?url=https://www.google.com
```

This will return a PNG image of the Google homepage.

## Contributing

We welcome contributions! Please follow these steps:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Ensure your code adheres to the project's style guidelines (pre-commit hooks will help with this).
5.  Write tests for your changes.
6.  Commit your changes (`git commit -m 'feat: Add new feature'`).
7.  Push to the branch (`git push origin feature/your-feature-name`).
8.  Open a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. (Note: You'll need to create a LICENSE file.)

## To-Do / Future Enhancements

*   Add unit and integration tests.
*   Implement more configurable options for screenshots (e.g., full page, specific element, dimensions).
*   Containerize the application using Docker.
*   Improve logging.

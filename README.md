# Web Scraper Analysis Tool

A powerful Flask-based web application that performs comprehensive analysis of websites by extracting and organizing various elements and metadata.

## Features

- **SEO Analysis**
  - Meta tags extraction
  - Open Graph and Twitter Card data
  - Title and description analysis
  - Canonical URL detection

- **Resource Analysis**
  - Scripts and stylesheets
  - Images and media files
  - Font resources
  - Third-party resources
  - Analytics tracking detection

- **Content Analysis**
  - Headings structure
  - Text content
  - Links and navigation
  - Form elements
  - Structured data (JSON-LD)

- **Security Analysis**
  - Security headers inspection
  - SSL/TLS information
  - Content Security Policy

- **Accessibility Features**
  - ARIA labels
  - Alt text verification
  - Form label checking
  - Color contrast analysis

- **Performance Metrics**
  - Resource count
  - Total size analysis
  - External resource tracking

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/web-scraper-analysis.git
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

## Usage

1. Open your browser and navigate to `http://localhost:5000`
2. Enter the URL you want to analyze
3. View the comprehensive analysis results

## Requirements

- Python 3.7+
- Flask
- BeautifulSoup4
- Requests
- PyLD
- Validators

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

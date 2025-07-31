# 🔒 Meta CAPI Event Connector

A production-ready FastAPI proxy that securely sends server-side events to Meta's Conversions API. Handles PII hashing, data validation, and payload formatting automatically - saving developers days of implementation time.

[![Live API](https://img.shields.io/badge/Live%20API-RapidAPI-blue)](https://rapidapi.com/studio/api_60948473-604c-406b-9489-5dabfcb741d2/publish/general)
[![Python](https://img.shields.io/badge/Python-3.8+-brightgreen)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-teal)](https://fastapi.tiangolo.com)

## 🎯 Problem Solved

Meta's Conversions API (CAPI) is powerful but complex to implement correctly. Most developers struggle with:

- **Security**: Properly hashing PII before transmission
- **Data Quality**: Capturing server-side signals (IP, User Agent) for better event matching
- **Validation**: Ensuring data meets Meta's strict requirements
- **Infrastructure**: Building, deploying, and maintaining server-side infrastructure

This API solves all of these problems in a single, production-ready service.

## ✨ Key Features

🔒 **Security First**
- Automatic SHA-256 hashing of all Personally Identifiable Information (PII)
- No raw user data stored or logged
- Secure credential handling via headers

⚡ **Production Ready**
- Comprehensive error handling with unique request IDs
- Detailed logging for debugging and monitoring
- Input validation and data cleaning
- Proper HTTP status codes and error responses

🎯 **Improved Data Quality**
- Server-side IP extraction (handles proxy headers)
- User Agent capture and validation
- Facebook Pixel ID format validation
- Currency/value relationship validation

🌐 **Universal Compatibility**
- Works with any CRM, e-commerce platform, or custom application
- RESTful API design with clear documentation
- Comprehensive example payloads

## 🚀 Quick Start

### 1. Clone and Install
```bash
git clone https://github.com/yourusername/meta-capi-proxy-demo.git
cd meta-capi-proxy-demo
pip install fastapi uvicorn requests pydantic
```

### 2. Set Up Environment
```bash
# Optional: Set environment variables for default credentials
export META_PIXEL_ID="your_pixel_id"
export META_ACCESS_TOKEN="your_access_token"
```

### 3. Run the API
```bash
python main.py
# or
uvicorn main:app --reload
```

### 4. View Documentation
Open `http://localhost:8000` in your browser to see the interactive API documentation.

## 📋 API Usage

### Send a Purchase Event
```bash
curl -X POST "http://localhost:8000/v1/process-event" \
  -H "Content-Type: application/json" \
  -H "X-Meta-Pixel-Id: YOUR_PIXEL_ID" \
  -H "X-Meta-Access-Token: YOUR_ACCESS_TOKEN" \
  -d '{
    "event_name": "Purchase",
    "event_time": 1703980800,
    "action_source": "website",
    "event_source_url": "https://example.com/checkout",
    "user_data": {
      "email": "customer@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone": "+1234567890",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    "custom_data": {
      "currency": "USD",
      "value": 99.99,
      "content_ids": ["product_123"],
      "content_type": "product"
    }
  }'
```

### Response
```json
{
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "success",
  "message": "Event processed and sent to Meta CAPI successfully",
  "meta_response": {
    "events_received": 1,
    "messages": [],
    "fbtrace_id": "A1B2C3D4E5F6G7H8"
  }
}
```

## 🏗️ Architecture

```
Client Application
       ↓ (HTTPS Request)
Meta CAPI Connector
       ↓ (Processes & Validates)
   [Hash PII] → [Extract Server Signals] → [Validate Data]
       ↓ (Secure HTTPS)
Meta Conversions API
```

### Data Flow
1. **Input**: Receives event data from any system
2. **Security**: Hashes all PII using SHA-256
3. **Enhancement**: Adds server-side signals (IP, User Agent)
4. **Validation**: Ensures data meets Meta's requirements
5. **Transmission**: Forwards to Meta CAPI
6. **Response**: Returns Meta's response with request tracking

## 🔧 Technical Details

### Dependencies
- **FastAPI**: Modern web framework for building APIs
- **Pydantic**: Data validation and serialization
- **Requests**: HTTP client for Meta API communication
- **Standard Library**: hashlib, ipaddress, uuid, re

### Security Features
- PII hashing using SHA-256
- Input validation and sanitization
- No data persistence or logging of sensitive information
- Secure credential handling via headers

### Error Handling
- Comprehensive HTTP error responses
- Unique request IDs for tracking and support
- Detailed logging for debugging
- Graceful handling of Meta API errors

## 🌟 Production Use

This code powers a live API serving clients globally. The production version includes:
- RapidAPI integration for easy scaling
- Enhanced monitoring and analytics
- Rate limiting and abuse protection
- Premium support channels

**Try the live API**: [Meta CAPI Connector on RapidAPI](https://rapidapi.com/studio/api_60948473-604c-406b-9489-5dabfcb741d2/publish/general)

## 📊 Business Impact

For marketing agencies and e-commerce businesses, this connector:
- **Saves 2-4 weeks** of development time
- **Improves ad performance** through better data quality
- **Ensures compliance** with privacy regulations
- **Reduces maintenance** burden of custom solutions

Typical implementation cost: **$5,000-15,000**  
This solution: **Ready in minutes**

## 🤝 Contributing

This is a demonstration repository showcasing production-quality code architecture. For feature requests or questions about custom implementations, please open an issue.

## 📄 License

MIT License - feel free to use this code as inspiration for your own projects.

---

**Built by Steven Lomon Lennartsson** 🌱

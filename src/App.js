import React, { useState, useRef, useEffect } from 'react';
import { Send, Mail, Phone, HelpCircle, Paperclip } from 'lucide-react';
import './App.css';

const App = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    setMessages([
      {
        text: "Hi there, Welcome to Secure Sense. We're here to help you stay protected from phishing emails and calls. We will analyze your emails or calls for suspicious activity, and we'll alert you of potential threats. Let's get started on securing your information! Select buttons below to choose your option.",
        sender: 'ai',
      },
    ]);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleInputChange = (e) => {
    setInputMessage(e.target.value);
  };

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (inputMessage.trim() || selectedFile) {
      if (selectedFile) {
        await sendFile(selectedFile);
      } else {
        await sendMessage(inputMessage, 'user');
      }
    }
  };

  const sendMessage = async (text, sender) => {
    setMessages((prevMessages) => [...prevMessages, { text, sender }]);
    setInputMessage('');

    if (sender === 'user') {
       
      try {
        const response = await fetch('http://localhost:5000/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: text,
            topic: selectedTopic,
          }),
        });

        if (!response.ok) {
          // Log the status code and status text for better insight
          throw new Error(`Request failed with status ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        const { tuned_response, flash_reasoning } = data;

        const newMessages = [{ text: tuned_response, sender: 'ai' }];

        if (flash_reasoning) {
          newMessages.push({ text: flash_reasoning, sender: 'ai' });
        }

        newMessages.push({
          text: 'Disclaimer: The analysis provided may contain inaccuracies. We encourage you to review the information and verify it independently before making any decisions.',
          sender: 'ai',
        });

        setMessages((prevMessages) => [...prevMessages, ...newMessages]);
      } catch (error) {
        console.error('Error:', error); // This will log the full error details to the console
        setMessages((prevMessages) => [
          ...prevMessages,
          { text: `Sorry, there was an error processing your request: ${error.message}`, sender: 'ai' }, // Display the error message in the chat
        ]);
      }
    }
};


  const sendFile = async (file) => {
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('http://127.0.0.1:5000/api/upload', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Failed to upload file');
        }

        const data = await response.json();
        
        // Display the transcribed text in the chat
        setMessages(prevMessages => [
            ...prevMessages,
            { text: 'Audio file uploaded and transcribed:', sender: 'ai' },
        ]);
        
        // Send the transcribed text to the /api/chat endpoint
        await sendMessage(data.transcription, 'user');

    } catch (error) {
        console.error('Error uploading file:', error);
        setMessages(prevMessages => [...prevMessages, { text: 'Error uploading file. Please try again.', sender: 'ai' }]);
    } finally {
        setIsUploading(false);
        setSelectedFile(null);
    }
};


  const handleTopicSelect = (topic) => {
    setSelectedTopic(topic);
    setSelectedFile(null);

    const topicMessages = [{ text: `I need help regarding ${topic}`, sender: 'user' }];

    if (topic === 'phishing email') {
      topicMessages.push({ text: 'Please paste your email to analyze in chat', sender: 'ai' });
    } else if (topic === 'spam calls') {
      topicMessages.push({ text: 'Please attach your call record to analyze in chat', sender: 'ai' });
    } else if (topic === 'general security advice') {
      topicMessages.push({
        text: "How can I assist with your security concerns today? Are you looking for tips on safeguarding your personal data, avoiding phishing scams, securing online accounts, or protecting your devices, I’m here to help. Is there anything specific you'd like advice on?",
        sender: 'ai',
      });
    }

    setMessages((prevMessages) => [...prevMessages, ...topicMessages]);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Secure Sense</h1>
      </header>
      <div className="messages-container">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`message ${message.sender === 'user' ? 'user-message' : 'ai-message'}`}
          >
            {message.text}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="topics-container">
        <button
          onClick={() => handleTopicSelect('phishing email')}
          className={`topic-button phishing-email ${selectedTopic === 'phishing email' ? 'selected' : ''}`}
        >
          <Mail size={16} className="icon" /> Phishing Email
        </button>
        <button
          onClick={() => handleTopicSelect('spam calls')}
          className={`topic-button spam-calls ${selectedTopic === 'spam calls' ? 'selected' : ''}`}
        >
          <Phone size={16} className="icon" /> Spam Calls
        </button>
        <button
          onClick={() => handleTopicSelect('general security advice')}
          className={`topic-button general-security-advice ${selectedTopic === 'general security advice' ? 'selected' : ''}`}
        >
          <HelpCircle size={16} className="icon" /> Security Advice
        </button>
      </div>
      <form onSubmit={handleSubmit} className="message-input-container">
        <div className="message-input-wrapper">
          <input
            type="text"
            value={inputMessage}
            onChange={handleInputChange}
            placeholder="Type your message here..."
            className="message-input"
            disabled={selectedTopic === 'spam calls' || isUploading}
          />
          {selectedTopic === 'spam calls' && (
            <>
              <input
                type="file"
                accept="audio/*"
                onChange={handleFileChange}
                ref={fileInputRef}
                style={{ display: 'none' }}
              />
              <Paperclip
                size={28}
                className="paperclip-icon"
                onClick={() => fileInputRef.current?.click()}
              />
            </>
          )}
          <button type="submit" className="message-send-button" disabled={isUploading}>
            <Send size={20} />
          </button>
        </div>
      </form>
      {isUploading && <div className="uploading-message">Uploading and transcribing audio...</div>}
    </div>
  );
};

export default App;
import React, {useState, useEffect} from 'react';

import './App.css';

const App = () => {
    const API_BASE = `${process.env.REACT_APP_SERVICE_ADDRESS}/api`;
    const [currentMessage, setCurrentMessage] = useState('');

    useEffect(() => {
        fetch(`${API_BASE}/message`)
            .then(res => res.text())
            .then(message => setCurrentMessage(message))
            .catch((err) => {
                console.error('error getting user message: ', err);
                setCurrentMessage('???');
            });
    }, [API_BASE]);

    const handleUserMessageKeyUp = (event) => {
        if (event.key === 'Enter') {
            const messageInput = event.target;
            let message = messageInput.value;
            console.log('user message: ' + message);

            fetch(`${API_BASE}/message`, {
                method: 'PUT',
                body: message
            })
                .then(res => res.text())
                .then(message => {
                    setCurrentMessage(message);
                    messageInput.value = ''
                })
                .catch((err) => {
                    console.error('error putting user message: ', err);
                    setCurrentMessage('???');
                })
        }
    };

    const currentMessageStyle = {
        whiteSpace: 'pre-wrap',
        fontFamily: 'monospace'
    }

    return <div>
        <input type="text" aria-label="Message" className="form-control" onKeyUp={handleUserMessageKeyUp}/>
        <div style={currentMessageStyle}>{currentMessage}</div>
    </div>
};

export default App;

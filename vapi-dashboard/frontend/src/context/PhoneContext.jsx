import { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const PhoneContext = createContext();

export function PhoneProvider({ children }) {
  const [phoneNumbers, setPhoneNumbers] = useState([]);
  const [selectedPhone, setSelectedPhone] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPhoneNumbers = async () => {
      try {
        const data = await api.getPhoneNumbers();
        const phones = data.phoneNumbers || [];
        setPhoneNumbers(phones);

        // Restore from localStorage or default to first
        const savedPhoneId = localStorage.getItem('selectedPhoneId');
        const savedPhone = phones.find(p => p.id === savedPhoneId);

        if (savedPhone) {
          setSelectedPhone(savedPhone);
        } else if (phones.length > 0) {
          setSelectedPhone(phones[0]);
        }
      } catch (err) {
        console.error('Failed to fetch phone numbers:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchPhoneNumbers();
  }, []);

  const selectPhone = (phoneId) => {
    const phone = phoneNumbers.find(p => p.id === phoneId);
    if (phone) {
      setSelectedPhone(phone);
      localStorage.setItem('selectedPhoneId', phoneId);
    }
  };

  return (
    <PhoneContext.Provider value={{
      phoneNumbers,
      selectedPhone,
      selectedPhoneId: selectedPhone?.id || '',
      selectPhone,
      loading
    }}>
      {children}
    </PhoneContext.Provider>
  );
}

export function usePhone() {
  const context = useContext(PhoneContext);
  if (!context) {
    throw new Error('usePhone must be used within a PhoneProvider');
  }
  return context;
}

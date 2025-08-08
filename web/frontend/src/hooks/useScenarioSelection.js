import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = window.location.hostname === 'localhost' ? '/api' : `http://${window.location.hostname}:8081/api`;

export const useScenarioSelection = () => {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenarios, setSelectedScenarios] = useState([]);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  useEffect(() => {
    // Fetch available scenarios
    axios.get(`${API_BASE_URL}/scenarios`)
      .then(response => {
        setScenarios(Array.isArray(response.data.scenarios) ? response.data.scenarios : []);
      })
      .catch(error => {
        setScenarios([]);
        console.error('Error fetching scenarios:', error);
      });
  }, []);

  const handleScenarioChange = (event) => {
    const value = event.target.value;

    // If selecting individual scenarios
    if (!value.includes('all')) {
      // If all individual scenarios are selected, switch to "all"
      if (value.length === scenarios.length) {
        setSelectedScenarios(['all']);
      } else {
        setSelectedScenarios(value);
      }
      return;
    }

    // If "all" is selected
    if (value.includes('all')) {
      // If "all" is the only selection, keep it
      if (value.length === 1) {
        setSelectedScenarios(['all']);
      } else {
        // If other scenarios are selected with "all", remove "all" and keep individual selections
        setSelectedScenarios(value.filter(v => v !== 'all'));
      }
    }
  };

  const handleScenarioChangeEnhanced = (event) => {
    const value = event.target.value;

    // If selecting individual scenarios
    if (!value.includes('all')) {
      // If all individual scenarios are selected, switch to "all"
      if (value.length === scenarios.length) {
        setSelectedScenarios(['all']);
      } else {
        setSelectedScenarios(value);
      }
      // Auto-close dropdown after selection
      setTimeout(() => setDropdownOpen(false), 100);
      return;
    }

    // If "all" is selected
    if (value.includes('all')) {
      // If "all" is the only selection, keep it
      if (value.length === 1) {
        setSelectedScenarios(['all']);
      } else {
        // If other scenarios are selected with "all", remove "all" and keep individual selections
        setSelectedScenarios(value.filter(v => v !== 'all'));
      }
      // Auto-close dropdown after selection
      setTimeout(() => setDropdownOpen(false), 100);
    }
  };

  const handleDropdownOpen = () => {
    setDropdownOpen(true);
  };

  const handleDropdownClose = () => {
    setDropdownOpen(false);
  };

  const getRenderValue = (selected) => {
    if (selected.includes('all')) return 'All Scenarios';
    if (selected.length === 0) return 'Select scenarios...';
    if (selected.length === 1) return selected[0];
    return `${selected.length} scenarios selected`;
  };

  return {
    scenarios,
    selectedScenarios,
    dropdownOpen,
    handleScenarioChange,
    handleScenarioChangeEnhanced,
    handleDropdownOpen,
    handleDropdownClose,
    getRenderValue
  };
}; 

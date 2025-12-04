import React, { useState, useEffect } from 'react';
import { fetchPerformanceHistory } from '../services/api';
import PerformanceHistoryTable from './PerformanceHistoryTable';

const PerformanceHistory = () => {
  const [performances, setPerformances] = useState([]);
  const [filteredPerformances, setFilteredPerformances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedGameweek, setSelectedGameweek] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(20);
  const [availableGameweeks, setAvailableGameweeks] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetchPerformanceHistory(1000); // Fetch more data for filtering/pagination
        setPerformances(response.data);
        
        // Extract unique gameweeks
        const gameweeks = [...new Set(response.data.map(p => p.gameweek))].sort((a, b) => b - a);
        setAvailableGameweeks(gameweeks);
      } catch (err) {
        setError('Failed to fetch performance history');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Filter performances based on selected gameweek
  useEffect(() => {
    let filtered = performances;
    
    if (selectedGameweek !== 'all') {
      filtered = performances.filter(p => p.gameweek === parseInt(selectedGameweek));
    }
    
    setFilteredPerformances(filtered);
    setCurrentPage(1); // Reset to first page when filter changes
  }, [selectedGameweek, performances]);

  // Get current performances for pagination
  const indexOfLastPerformance = currentPage * itemsPerPage;
  const indexOfFirstPerformance = indexOfLastPerformance - itemsPerPage;
  const currentPerformances = filteredPerformances.slice(indexOfFirstPerformance, indexOfLastPerformance);
  const totalPages = Math.ceil(filteredPerformances.length / itemsPerPage);

  // Change page
  const paginate = (pageNumber) => setCurrentPage(pageNumber);

  if (loading) {
    return <div className="loading">Loading performance history...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div>
      <h1>Performance History</h1>
      
      {/* Gameweek Filter */}
      <div className="filter-section">
        <label htmlFor="gameweek-filter">Filter by Gameweek: </label>
        <select 
          id="gameweek-filter"
          value={selectedGameweek} 
          onChange={(e) => setSelectedGameweek(e.target.value)}
          className="filter-dropdown"
        >
          <option value="all">All Gameweeks</option>
          {availableGameweeks.map(gw => (
            <option key={gw} value={gw}>Gameweek {gw}</option>
          ))}
        </select>
      </div>
      
      <PerformanceHistoryTable performances={currentPerformances} />
      
      {/* Pagination */}
      {filteredPerformances.length > 0 && (
        <div className="pagination">
          <button 
            onClick={() => paginate(currentPage - 1)} 
            disabled={currentPage === 1}
            className="pagination-btn"
          >
            Previous
          </button>
          
          <span className="pagination-info">
            Page {currentPage} of {totalPages}
          </span>
          
          <button 
            onClick={() => paginate(currentPage + 1)} 
            disabled={currentPage === totalPages}
            className="pagination-btn"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );

};

export default PerformanceHistory;
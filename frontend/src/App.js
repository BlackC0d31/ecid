import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const InsuranceProviders = {
  ALLIANZ: "allianz",
  UNIPOLSAI: "unipolsai", 
  GENERALI: "generali",
  AXA: "axa"
};

const CIDStatus = {
  PENDING: "pending",
  SUBMITTED: "submitted",
  APPROVED: "approved",
  REJECTED: "rejected",
  ERROR: "error"
};

function App() {
  const [activeTab, setActiveTab] = useState("submit");
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

  // Form state
  const [formData, setFormData] = useState({
    person_a: {
      name: "",
      surname: "",
      license_plate: "",
      insurance_company: InsuranceProviders.ALLIANZ,
      policy_number: ""
    },
    person_b: {
      name: "",
      surname: "",
      license_plate: "",
      insurance_company: InsuranceProviders.ALLIANZ,
      policy_number: ""
    },
    accident_details: {
      timestamp: "",
      location: "",
      description: "",
      circumstances: [],
      damage_description: ""
    }
  });

  const [pdfFile, setPdfFile] = useState(null);
  const [pdfData, setPdfData] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [searchClaimId, setSearchClaimId] = useState("");

  useEffect(() => {
    checkHealth();
    loadSubmissions();
  }, []);

  const checkHealth = async () => {
    try {
      const response = await axios.get(`${API}/health`);
      console.log("API Health:", response.data);
    } catch (error) {
      console.error("API Health check failed:", error);
    }
  };

  const loadSubmissions = async () => {
    try {
      const response = await axios.get(`${API}/cids`);
      setSubmissions(response.data);
    } catch (error) {
      console.error("Error loading submissions:", error);
    }
  };

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: "", text: "" }), 5000);
  };

  const handleInputChange = (section, field, value) => {
    if (section === "accident_details" && field === "circumstances") {
      setFormData(prev => ({
        ...prev,
        [section]: {
          ...prev[section],
          [field]: value.split(",").map(item => item.trim()).filter(item => item)
        }
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [section]: {
          ...prev[section],
          [field]: value
        }
      }));
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (file.type !== "application/pdf") {
      showMessage("error", "Please select a PDF file");
      return;
    }

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await axios.post(`${API}/cid/upload-pdf`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      setPdfFile(file);
      setPdfData(response.data);
      showMessage("success", `PDF uploaded successfully. Hash: ${response.data.hash.substring(0, 16)}...`);
    } catch (error) {
      showMessage("error", "Error uploading PDF: " + (error.response?.data?.detail || error.message));
    }
    setIsLoading(false);
  };

  const validateForm = () => {
    const required = [
      formData.person_a.name,
      formData.person_a.surname,
      formData.person_a.license_plate,
      formData.person_a.policy_number,
      formData.person_b.name,
      formData.person_b.surname,
      formData.person_b.license_plate,
      formData.person_b.policy_number,
      formData.accident_details.location,
      formData.accident_details.description,
      formData.accident_details.damage_description
    ];

    return required.every(field => field && field.trim().length > 0) && 
           formData.accident_details.circumstances.length > 0 &&
           pdfData;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!validateForm()) {
      showMessage("error", "Please fill all required fields and upload a PDF");
      return;
    }

    setIsLoading(true);
    try {
      const submissionData = {
        cid_data: {
          ...formData,
          accident_details: {
            ...formData.accident_details,
            timestamp: formData.accident_details.timestamp || new Date().toISOString()
          }
        },
        pdf_base64: pdfData.base64,
        pdf_hash: pdfData.hash
      };

      const response = await axios.post(`${API}/cid/submit`, submissionData);

      showMessage("success", `CID submitted successfully! Claim ID: ${response.data.claim_id}`);
      
      // Reset form
      setFormData({
        person_a: { name: "", surname: "", license_plate: "", insurance_company: InsuranceProviders.ALLIANZ, policy_number: "" },
        person_b: { name: "", surname: "", license_plate: "", insurance_company: InsuranceProviders.ALLIANZ, policy_number: "" },
        accident_details: { timestamp: "", location: "", description: "", circumstances: [], damage_description: "" }
      });
      setPdfFile(null);
      setPdfData(null);
      
      // Reload submissions
      loadSubmissions();
      
    } catch (error) {
      showMessage("error", "Error submitting CID: " + (error.response?.data?.detail || error.message));
    }
    setIsLoading(false);
  };

  const searchCID = async () => {
    if (!searchClaimId.trim()) {
      showMessage("error", "Please enter a claim ID");
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.get(`${API}/cid/${searchClaimId}`);
      showMessage("success", `CID found! Status: ${response.data.status}`);
      // You could display more details here
    } catch (error) {
      showMessage("error", "CID not found or error occurred");
    }
    setIsLoading(false);
  };

  const getStatusColor = (status) => {
    const colors = {
      [CIDStatus.PENDING]: "text-yellow-600 bg-yellow-100",
      [CIDStatus.SUBMITTED]: "text-blue-600 bg-blue-100",
      [CIDStatus.APPROVED]: "text-green-600 bg-green-100",
      [CIDStatus.REJECTED]: "text-red-600 bg-red-100",
      [CIDStatus.ERROR]: "text-red-800 bg-red-200"
    };
    return colors[status] || "text-gray-600 bg-gray-100";
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">CID Insurance System</h1>
                <p className="text-gray-600">Digital Amicable Accident Report Processing</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Message Display */}
      {message.text && (
        <div className={`max-w-7xl mx-auto px-4 py-2`}>
          <div className={`p-4 rounded-md ${message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
            {message.text}
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex space-x-1 bg-white p-1 rounded-lg shadow-sm">
          {[
            { id: "submit", label: "Submit CID", icon: "📝" },
            { id: "track", label: "Track CID", icon: "🔍" },
            { id: "history", label: "History", icon: "📋" }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-md font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-blue-600 text-white shadow-md"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 pb-12">
        {activeTab === "submit" && (
          <div className="bg-white rounded-xl shadow-lg p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Submit New CID</h2>
            
            <form onSubmit={handleSubmit} className="space-y-8">
              {/* Person A */}
              <div className="border-l-4 border-blue-500 pl-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Person A Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Name *</label>
                    <input
                      type="text"
                      value={formData.person_a.name}
                      onChange={(e) => handleInputChange("person_a", "name", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Surname *</label>
                    <input
                      type="text"
                      value={formData.person_a.surname}
                      onChange={(e) => handleInputChange("person_a", "surname", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">License Plate *</label>
                    <input
                      type="text"
                      value={formData.person_a.license_plate}
                      onChange={(e) => handleInputChange("person_a", "license_plate", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Insurance Company *</label>
                    <select
                      value={formData.person_a.insurance_company}
                      onChange={(e) => handleInputChange("person_a", "insurance_company", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    >
                      {Object.entries(InsuranceProviders).map(([key, value]) => (
                        <option key={value} value={value}>{key}</option>
                      ))}
                    </select>
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Policy Number *</label>
                    <input
                      type="text"
                      value={formData.person_a.policy_number}
                      onChange={(e) => handleInputChange("person_a", "policy_number", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Person B */}
              <div className="border-l-4 border-green-500 pl-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Person B Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Name *</label>
                    <input
                      type="text"
                      value={formData.person_b.name}
                      onChange={(e) => handleInputChange("person_b", "name", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Surname *</label>
                    <input
                      type="text"
                      value={formData.person_b.surname}
                      onChange={(e) => handleInputChange("person_b", "surname", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">License Plate *</label>
                    <input
                      type="text"
                      value={formData.person_b.license_plate}
                      onChange={(e) => handleInputChange("person_b", "license_plate", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Insurance Company *</label>
                    <select
                      value={formData.person_b.insurance_company}
                      onChange={(e) => handleInputChange("person_b", "insurance_company", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      required
                    >
                      {Object.entries(InsuranceProviders).map(([key, value]) => (
                        <option key={value} value={value}>{key}</option>
                      ))}
                    </select>
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Policy Number *</label>
                    <input
                      type="text"
                      value={formData.person_b.policy_number}
                      onChange={(e) => handleInputChange("person_b", "policy_number", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Accident Details */}
              <div className="border-l-4 border-orange-500 pl-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Accident Details</h3>
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Date & Time</label>
                      <input
                        type="datetime-local"
                        value={formData.accident_details.timestamp}
                        onChange={(e) => handleInputChange("accident_details", "timestamp", e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Location *</label>
                      <input
                        type="text"
                        value={formData.accident_details.location}
                        onChange={(e) => handleInputChange("accident_details", "location", e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                        placeholder="Street address, city, country"
                        required
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Accident Description *</label>
                    <textarea
                      value={formData.accident_details.description}
                      onChange={(e) => handleInputChange("accident_details", "description", e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent h-24"
                      placeholder="Describe what happened..."
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Circumstances (comma-separated) *</label>
                    <input
                      type="text"
                      value={formData.accident_details.circumstances.join(", ")}
                      onChange={(e) => handleInputChange("accident_details", "circumstances", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                      placeholder="Weather conditions, road conditions, visibility, etc."
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Damage Description *</label>
                    <textarea
                      value={formData.accident_details.damage_description}
                      onChange={(e) => handleInputChange("accident_details", "damage_description", e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent h-24"
                      placeholder="Describe the damage to vehicles..."
                      required
                    />
                  </div>
                </div>
              </div>

              {/* PDF Upload */}
              <div className="border-l-4 border-purple-500 pl-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Signed PDF Document</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Upload CID PDF *</label>
                    <input
                      type="file"
                      accept=".pdf"
                      onChange={handleFileUpload}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"
                      required
                    />
                  </div>
                  {pdfData && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <p className="text-sm text-gray-600">
                        <strong>File:</strong> {pdfFile.name} ({(pdfFile.size / 1024 / 1024).toFixed(2)} MB)
                      </p>
                      <p className="text-sm text-gray-600">
                        <strong>Hash:</strong> {pdfData.hash.substring(0, 32)}...
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Submit Button */}
              <div className="pt-6 border-t border-gray-200">
                <button
                  type="submit"
                  disabled={isLoading || !validateForm()}
                  className="w-full bg-blue-600 text-white py-3 px-8 rounded-lg font-semibold text-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                >
                  {isLoading ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      <span>Processing...</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                      </svg>
                      <span>Submit CID to Insurance Companies</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}

        {activeTab === "track" && (
          <div className="bg-white rounded-xl shadow-lg p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Track CID Status</h2>
            
            <div className="space-y-6">
              <div className="flex space-x-4">
                <input
                  type="text"
                  value={searchClaimId}
                  onChange={(e) => setSearchClaimId(e.target.value)}
                  placeholder="Enter Claim ID (e.g., CID-1234567890-abcd1234)"
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <button
                  onClick={searchCID}
                  disabled={isLoading}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {isLoading ? "Searching..." : "Search"}
                </button>
              </div>

              <div className="bg-gray-50 p-6 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">How to track your CID:</h3>
                <ol className="list-decimal list-inside space-y-2 text-gray-700">
                  <li>Enter your Claim ID in the search box above</li>
                  <li>Click "Search" to retrieve the current status</li>
                  <li>View processing details and insurance company responses</li>
                </ol>
              </div>
            </div>
          </div>
        )}

        {activeTab === "history" && (
          <div className="bg-white rounded-xl shadow-lg p-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Submission History</h2>
              <button
                onClick={loadSubmissions}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors"
              >
                Refresh
              </button>
            </div>

            {submissions.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-24 h-24 mx-auto mb-4 text-gray-300">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <p className="text-gray-500 text-lg">No CID submissions yet</p>
                <p className="text-gray-400">Submit your first CID to see it here</p>
              </div>
            ) : (
              <div className="space-y-4">
                {submissions.map((submission, index) => (
                  <div key={index} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          Claim ID: {submission.claim_id}
                        </h3>
                        <p className="text-sm text-gray-600">
                          Submitted: {new Date(submission.created_at).toLocaleString()}
                        </p>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(submission.status)}`}>
                        {submission.status.toUpperCase()}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
                      <div>
                        <strong>Person A:</strong> {submission.cid_data?.person_a?.name} {submission.cid_data?.person_a?.surname}
                        <br />
                        <strong>Insurance:</strong> {submission.cid_data?.person_a?.insurance_company?.toUpperCase()}
                      </div>
                      <div>
                        <strong>Person B:</strong> {submission.cid_data?.person_b?.name} {submission.cid_data?.person_b?.surname}
                        <br />
                        <strong>Insurance:</strong> {submission.cid_data?.person_b?.insurance_company?.toUpperCase()}
                      </div>
                    </div>

                    {submission.api_responses && submission.api_responses.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <strong className="text-sm text-gray-700">API Responses:</strong>
                        <div className="mt-2 space-y-2">
                          {submission.api_responses.map((response, respIndex) => (
                            <div key={respIndex} className="bg-gray-50 p-3 rounded text-sm">
                              <div className="flex items-center justify-between">
                                <span className="font-medium">{response.provider.toUpperCase()}</span>
                                <span className={`px-2 py-1 rounded text-xs ${response.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                  {response.success ? 'SUCCESS' : 'ERROR'}
                                </span>
                              </div>
                              {response.claim_id && (
                                <p className="text-gray-600 mt-1">Provider Claim ID: {response.claim_id}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
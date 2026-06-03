import { useState } from 'react'
import '../../styles/crisis-modal.css'

const CRISIS_RESOURCES = {
  english: {
    title: 'Crisis Support Resources',
    subtitle: 'You are not alone. Help is available 24/7',
    footer: 'If you\'re in immediate danger, please call emergency services (911 in US, 112 in India, 999 in Bangladesh) or visit your nearest hospital.',
    resources: [
      {
        name: 'National Suicide Prevention Lifeline',
        phone: '1-800-273-8255',
        website: 'https://suicidepreventionlifeline.org',
        description: 'Free and confidential support 24/7'
      },
      {
        name: 'Crisis Text Line',
        phone: 'Text HOME to 741741',
        website: 'https://www.crisistextline.org',
        description: 'Text-based crisis support'
      },
      {
        name: 'International Association for Suicide Prevention',
        phone: 'https://www.iasp.info/resources/Crisis_Centres/',
        website: 'https://www.iasp.info/resources/Crisis_Centres/',
        description: 'Find crisis centers worldwide'
      },
      {
        name: 'Befrienders',
        phone: '1-800-273-8255',
        website: 'https://www.befrienders.org',
        description: 'Emotional support helpline'
      }
    ]
  },
  hindi: {
    title: 'संकट समर्थन संसाधन',
    subtitle: 'आप अकेले नहीं हैं। 24/7 सहायता उपलब्ध है',
    footer: 'अगर आप तुरंत खतरे में हैं, तो कृपया आपातकालीन सेवाएं (भारत में 112) को कॉल करें या अपने निकटतम अस्पताल में जाएं।',
    resources: [
      {
        name: 'आसरा संकट हेल्पलाइन',
        phone: '9820466726',
        website: 'https://www.asararesearch.org',
        description: 'मानसिक स्वास्थ्य सहायता'
      },
      {
        name: 'iCall संकट लाइन',
        phone: '9152987821',
        website: 'https://www.icallhelpline.org',
        description: 'युवाओं के लिए भावनात्मक सहायता'
      },
      {
        name: 'AASRA',
        phone: '022-27546669',
        website: 'https://www.aasra.info',
        description: 'आत्महत्या रोकथाम केंद्र'
      },
      {
        name: 'इंदौर मानसिक स्वास्थ्य केंद्र',
        phone: '+91-731-2445800',
        website: 'https://imhcindore.org',
        description: '24 घंटे संकट हस्तक्षेप सेवा'
      }
    ]
  },
  bengali: {
    title: 'সংকট সহায়তা সম্পদ',
    subtitle: 'আপনি একা নন। 24/7 সাহায্য পাওয়া যায়',
    footer: 'যদি আপনি তাৎক্ষণিক বিপদে থাকেন, তবে জরুরি সেবা (বাংলাদেশে 999) কল করুন বা আপনার নিকটতম হাসপাতালে যান।',
    resources: [
      {
        name: 'ঢাকা মানসিক স্বাস্থ্য কেন্দ্র',
        phone: '+880-2-9611401',
        website: 'https://www.dmch.gov.bd',
        description: 'জরুরি মানসিক স্বাস্থ্য সহায়তা'
      },
      {
        name: 'সাপোর্ট ফোন লাইন',
        phone: '09613002002',
        website: 'https://www.supportline.com.bd',
        description: '24 ঘন্টা আবেগময় সহায়তা'
      },
      {
        name: 'জাতীয় মানসিক স্বাস্থ্য সংস্থান',
        phone: '+880-2-8828850',
        website: 'https://www.nmhi.gov.bd',
        description: 'সংকট হস্তক্ষেপ দল'
      },
      {
        name: 'ঘরে বসে সেবা (হট লাইন)',
        phone: '01819-277374',
        website: 'https://www.ghorbose.org',
        description: 'সহায়তা এবং পরামর্শ'
      }
    ]
  }
}

export default function CrisisModal({ isOpen, onClose, language = 'english' }) {
  const [expandedIndex, setExpandedIndex] = useState(null)
  
  if (!isOpen) return null

  const resourceData = CRISIS_RESOURCES[language] || CRISIS_RESOURCES.english

  const handleResourceClick = (website) => {
    if (website && (website.startsWith('http://') || website.startsWith('https://'))) {
      window.open(website, '_blank', 'noopener,noreferrer')
    }
  }

  return (
    <div className="crisis-modal-overlay" onClick={onClose}>
      <div className="crisis-modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Close Button */}
        <button className="crisis-modal-close" onClick={onClose} title="Close">
          ✕
        </button>

        {/* Header */}
        <div className="crisis-modal-header">
          <h2>{resourceData.title}</h2>
          <p className="crisis-modal-subtitle">{resourceData.subtitle}</p>
        </div>

        {/* Resources Grid */}
        <div className="crisis-resources-container">
          {resourceData.resources.map((resource, index) => (
            <div key={index} className="crisis-resource-card">
              <div className="resource-header" onClick={() => setExpandedIndex(expandedIndex === index ? null : index)}>
                <h3>{resource.name}</h3>
                <span className="expand-icon">
                  {expandedIndex === index ? '−' : '+'}
                </span>
              </div>
              
              {expandedIndex === index && (
                <div className="resource-details">
                  <p className="resource-description">{resource.description}</p>
                  
                  {resource.phone && (
                    <div className="resource-contact">
                      <span className="contact-label">Phone:</span>
                      <a href={resource.phone.startsWith('+') || resource.phone.startsWith('0') ? `tel:${resource.phone.replace(/\D/g, '')}` : 'javascript:void(0)'}  className="contact-value">
                        {resource.phone}
                      </a>
                    </div>
                  )}
                  
                  {resource.website && (
                    <button 
                      className="resource-link-btn"
                      onClick={() => handleResourceClick(resource.website)}
                    >
                      Visit Website →
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Footer Message */}
        <div className="crisis-modal-footer">
          <p>{resourceData.footer}</p>
        </div>
      </div>
    </div>
  )
}

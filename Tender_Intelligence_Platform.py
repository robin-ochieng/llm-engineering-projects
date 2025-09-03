# Actuarial Business Development & Tender Intelligence Platform
# Automated tender monitoring and lead generation for actuarial advisory services

import os
import requests
import json
import csv
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum
import time
import logging
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from dotenv import load_dotenv
from bs4 import BeautifulSoup
# Make IPython optional in non-notebook environments
try:
    from IPython.display import Markdown, display  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    def display(x):  # minimal fallback
        print(str(x))
    class Markdown(str):
        pass
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TenderStatus(Enum):
    OPEN = "open"
    CLOSING_SOON = "closing_soon"  # Within 7 days
    CLOSED = "closed"
    AWARDED = "awarded"

class OpportunityScore(Enum):
    HIGH = "high"       # 80-100% match
    MEDIUM = "medium"   # 50-79% match
    LOW = "low"        # 20-49% match
    MINIMAL = "minimal" # <20% match

class ServiceArea(Enum):
    IFRS17 = "ifrs17"
    PENSION_CONSULTING = "pension_consulting"
    ERM = "enterprise_risk_management"
    ESG_CONSULTING = "esg_consulting"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    ACTUARIAL_SERVICES = "actuarial_services"
    INVESTMENT_CONSULTING = "investment_consulting"
    GOVERNANCE_RISK = "governance_risk"

@dataclass
class TenderSite:
    """Represents a tender/procurement website to monitor"""
    url: str
    name: str
    country: str
    sector: str  # government, private, international
    search_params: Dict[str, str]  # Site-specific search parameters
    requires_login: bool = False
    check_frequency: int = 24  # Hours between checks
    last_checked: Optional[datetime] = None
    active: bool = True

@dataclass
class TenderOpportunity:
    """Represents a tender opportunity"""
    title: str
    description: str
    tender_id: str
    source_site: str
    url: str
    client_organization: str
    publication_date: datetime
    closing_date: Optional[datetime]
    estimated_value: Optional[str]
    location: str
    status: TenderStatus
    service_areas_matched: List[ServiceArea]
    keywords_matched: List[str]
    opportunity_score: OpportunityScore
    ai_analysis: str
    recommended_team: List[str]
    competition_level: str  # High/Medium/Low
    win_probability: str   # High/Medium/Low
    submission_requirements: List[str]
    contact_information: Dict[str, str]
    documents_available: List[str]
    timestamp: datetime

@dataclass
class LeadReport:
    """Business development lead report"""
    opportunity: TenderOpportunity
    business_case: str
    proposed_approach: str
    team_requirements: str
    budget_estimate: str
    risk_assessment: str
    next_steps: List[str]
    deadline_tracker: str

class ActuarialTenderAnalyzer:
    """AI-powered analyzer for actuarial tender opportunities"""
    
    def __init__(self, api_key: str):
        self.openai = OpenAI(api_key=api_key)
        
        # Actuarial service keywords categorized
        self.service_keywords = {
            ServiceArea.IFRS17: [
                "IFRS 17", "ifrs17", "insurance contracts", "financial reporting", 
                "contract boundaries", "CSM", "risk adjustment", "onerous contracts",
                "premium allocation approach", "general measurement model"
            ],
            ServiceArea.PENSION_CONSULTING: [
                "pension", "retirement", "actuarial valuation", "pension scheme",
                "pension fund", "retirement solutions", "defined benefit", "defined contribution",
                "pension regulations", "pension audit", "pension risk", "retirement planning"
            ],
            ServiceArea.ERM: [
                "enterprise risk management", "ERM", "risk framework", "risk appetite",
                "risk modelling", "risk assessment", "risk quantification", "stress testing",
                "scenario analysis", "risk governance", "risk based capital", "solvency"
            ],
            ServiceArea.ESG_CONSULTING: [
                "ESG", "sustainability", "climate risk", "environmental risk",
                "social responsibility", "governance", "sustainable finance",
                "climate change", "carbon footprint", "green finance"
            ],
            ServiceArea.REGULATORY_COMPLIANCE: [
                "regulatory compliance", "regulatory affairs", "compliance audit",
                "statutory reporting", "regulatory policy", "financial regulation",
                "prudential regulation", "capital requirements", "regulatory framework"
            ],
            ServiceArea.ACTUARIAL_SERVICES: [
                "actuarial", "actuarial services", "actuarial analysis", "actuarial valuation",
                "actuarial consulting", "actuarial audit", "reserving", "pricing",
                "product development", "embedded value", "financial condition"
            ],
            ServiceArea.INVESTMENT_CONSULTING: [
                "investment consulting", "asset liability matching", "investment policy",
                "portfolio management", "investment strategy", "asset allocation",
                "investment risk", "market risk", "ALM", "asset liability"
            ],
            ServiceArea.GOVERNANCE_RISK: [
                "governance", "corporate governance", "risk governance", "board advisory",
                "risk committee", "audit committee", "governance framework",
                "risk culture", "governance training", "risk oversight"
            ]
        }
        
        # All keywords flattened for searching
        self.all_keywords = []
        for keywords_list in self.service_keywords.values():
            self.all_keywords.extend(keywords_list)
    
    def analyze_tender(self, tender_text: str, tender_title: str, tender_url: str) -> Tuple[OpportunityScore, List[ServiceArea], str]:
        """Analyze tender content for actuarial relevance and opportunity score"""
        
        # Find matching keywords and service areas
        matched_keywords = self._find_keywords(tender_text + " " + tender_title)
        matched_service_areas = self._identify_service_areas(matched_keywords)
        
        # Calculate opportunity score based on keyword matches and context
        opportunity_score = self._calculate_opportunity_score(matched_keywords, tender_text)
        
        # Generate AI analysis
        ai_analysis = self._generate_ai_analysis(tender_text, tender_title, matched_service_areas)
        
        return opportunity_score, matched_service_areas, ai_analysis
    
    def _find_keywords(self, text: str) -> List[str]:
        """Find matching keywords in tender text"""
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.all_keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def _identify_service_areas(self, keywords: List[str]) -> List[ServiceArea]:
        """Identify which service areas match based on keywords"""
        matched_areas = []
        
        for service_area, area_keywords in self.service_keywords.items():
            for keyword in keywords:
                if keyword in area_keywords:
                    if service_area not in matched_areas:
                        matched_areas.append(service_area)
                    break
        
        return matched_areas
    
    def _calculate_opportunity_score(self, keywords: List[str], tender_text: str) -> OpportunityScore:
        """Calculate opportunity score based on keyword matches and context"""
        
        # Base score from keyword matches
        keyword_score = min(len(keywords) * 10, 60)  # Max 60 points from keywords
        
        # Context scoring using AI
        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"""
                    Score this tender opportunity for an actuarial advisory firm on a scale of 0-40 (additional context points):
                    
                    Consider:
                    - How closely the requirements match actuarial services
                    - Complexity and scope of work
                    - Potential for follow-on work
                    - Strategic value for the firm
                    
                    Tender text: {tender_text[:1000]}
                    
                    Return only a number between 0-40.
                    """
                }]
            )
            
            context_score = int(response.choices[0].message.content.strip())
            context_score = max(0, min(40, context_score))  # Ensure 0-40 range
            
        except:
            context_score = 20  # Default moderate score
        
        total_score = keyword_score + context_score
        
        if total_score >= 80:
            return OpportunityScore.HIGH
        elif total_score >= 50:
            return OpportunityScore.MEDIUM
        elif total_score >= 20:
            return OpportunityScore.LOW
        else:
            return OpportunityScore.MINIMAL
    
    def _generate_ai_analysis(self, tender_text: str, title: str, service_areas: List[ServiceArea]) -> str:
        """Generate detailed AI analysis of the tender opportunity"""
        
        service_areas_text = ", ".join([area.value.replace("_", " ").title() for area in service_areas])
        
        system_prompt = """You are a senior business development manager for an actuarial advisory firm specializing in insurance, pensions, risk management, and regulatory compliance. Analyze tender opportunities and provide strategic business insights."""
        
        user_prompt = f"""
        Analyze this tender opportunity:
        
        Title: {title}
        Matched Service Areas: {service_areas_text}
        
        Tender Content: {tender_text[:2000]}
        
        Provide a concise analysis covering:
        1. Key requirements and how they align with our actuarial services
        2. Potential scope of work and engagement size
        3. Strategic value and growth potential
        4. Competitive landscape assessment
        5. Recommended approach and team composition
        6. Risk factors and challenges
        
        Keep response to 300-400 words, focused on actionable business insights.
        """
        
        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating AI analysis: {str(e)}")
            return f"Analysis error occurred. Manual review required. Matched areas: {service_areas_text}"

class TenderScraper:
    """Enhanced web scraper for tender/procurement sites"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_tender_site(self, site: TenderSite, keywords: List[str]) -> List[TenderOpportunity]:
        """Scrape a tender site for relevant opportunities"""
        
        opportunities = []
        
        if site.name.lower() in ['ungm', 'united nations']:
            opportunities.extend(self._scrape_ungm(site, keywords))
        elif site.name.lower() in ['world bank', 'worldbank']:
            opportunities.extend(self._scrape_worldbank(site, keywords))
        elif 'ted' in site.name.lower() or 'europa' in site.url:
            opportunities.extend(self._scrape_ted(site, keywords))
        else:
            # Generic scraping approach
            opportunities.extend(self._generic_scrape(site, keywords))
        
        return opportunities
    
    def _scrape_ungm(self, site: TenderSite, keywords: List[str]) -> List[TenderOpportunity]:
        """Specific scraper for UN Global Marketplace"""
        opportunities = []
        
        try:
            # UNGM search URL with actuarial/financial keywords
            search_url = "https://www.ungm.org/Public/Notice"
            
            # Use Selenium for JavaScript-heavy sites
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            driver.get(search_url)
            time.sleep(5)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find tender listings (adapt selectors based on actual site structure)
            tender_cards = soup.find_all('div', class_='notice-card') or soup.find_all('tr', class_='notice-row')
            
            for card in tender_cards[:20]:  # Limit to first 20 results
                opportunity = self._extract_tender_info(card, site)
                if opportunity and self._contains_relevant_keywords(opportunity.title + " " + opportunity.description, keywords):
                    opportunities.append(opportunity)
            
            driver.quit()
            
        except Exception as e:
            logger.error(f"Error scraping UNGM: {str(e)}")
        
        return opportunities
    
    def _scrape_worldbank(self, site: TenderSite, keywords: List[str]) -> List[TenderOpportunity]:
        """Specific scraper for World Bank eProcurement"""
        opportunities = []
        
        try:
            # World Bank procurement search
            search_url = "https://projects.worldbank.org/en/projects-operations/procurement"
            
            response = self.session.get(search_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract procurement opportunities
            proc_items = soup.find_all('div', class_='procurement-item') or soup.find_all('a', href=re.compile('procurement'))
            
            for item in proc_items[:15]:
                opportunity = self._extract_tender_info(item, site)
                if opportunity and self._contains_relevant_keywords(opportunity.title + " " + opportunity.description, keywords):
                    opportunities.append(opportunity)
            
        except Exception as e:
            logger.error(f"Error scraping World Bank: {str(e)}")
        
        return opportunities
    
    def _scrape_ted(self, site: TenderSite, keywords: List[str]) -> List[TenderOpportunity]:
        """Specific scraper for TED (Tenders Electronic Daily)"""
        opportunities = []
        
        try:
            # TED search for financial/consulting services
            search_url = "https://ted.europa.eu/udl"
            
            response = self.session.get(search_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract tender notices
            notices = soup.find_all('div', class_='notice') or soup.find_all('article', class_='tender')
            
            for notice in notices[:15]:
                opportunity = self._extract_tender_info(notice, site)
                if opportunity and self._contains_relevant_keywords(opportunity.title + " " + opportunity.description, keywords):
                    opportunities.append(opportunity)
            
        except Exception as e:
            logger.error(f"Error scraping TED: {str(e)}")
        
        return opportunities
    
    def _generic_scrape(self, site: TenderSite, keywords: List[str]) -> List[TenderOpportunity]:
        """Generic scraping approach for other tender sites"""
        opportunities = []
        
        try:
            response = self.session.get(site.url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Common selectors for tender listings
            tender_selectors = [
                '.tender', '.opportunity', '.notice', '.procurement',
                '[class*="tender"]', '[class*="opportunity"]'
            ]
            
            tender_items = []
            for selector in tender_selectors:
                items = soup.select(selector)
                if items:
                    tender_items = items
                    break
            
            for item in tender_items[:20]:
                opportunity = self._extract_tender_info(item, site)
                if opportunity and self._contains_relevant_keywords(opportunity.title + " " + opportunity.description, keywords):
                    opportunities.append(opportunity)
            
        except Exception as e:
            logger.error(f"Error scraping {site.name}: {str(e)}")
        
        return opportunities
    
    def _extract_tender_info(self, element, site: TenderSite) -> Optional[TenderOpportunity]:
        """Extract tender information from HTML element"""
        try:
            # Extract basic information (adapt selectors based on site structure)
            title = self._extract_text(element, ['h1', 'h2', 'h3', '.title', '.notice-title'])
            description = self._extract_text(element, ['.description', '.summary', 'p'])
            
            if not title:
                return None
            
            # Extract other fields
            tender_id = self._extract_text(element, ['.id', '.reference', '.number']) or f"AUTO_{hash(title)}"
            closing_date = self._extract_date(element, ['.closing', '.deadline', '.date'])
            estimated_value = self._extract_text(element, ['.value', '.amount', '.budget'])
            location = self._extract_text(element, ['.location', '.country', '.region'])
            
            # Get URL
            url_element = element.find('a')
            tender_url = url_element['href'] if url_element else site.url
            if tender_url.startswith('/'):
                tender_url = urljoin(site.url, tender_url)
            
            return TenderOpportunity(
                title=title[:200],
                description=description[:1000],
                tender_id=tender_id,
                source_site=site.name,
                url=tender_url,
                client_organization=site.name,  # Will be updated with actual org if found
                publication_date=datetime.now(),
                closing_date=closing_date,
                estimated_value=estimated_value,
                location=location or site.country,
                status=TenderStatus.OPEN,  # Will be determined later
                service_areas_matched=[],
                keywords_matched=[],
                opportunity_score=OpportunityScore.LOW,
                ai_analysis="",
                recommended_team=[],
                competition_level="Medium",
                win_probability="Medium",
                submission_requirements=[],
                contact_information={},
                documents_available=[],
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error extracting tender info: {str(e)}")
            return None
    
    def _extract_text(self, element, selectors: List[str]) -> str:
        """Extract text using multiple selector attempts"""
        for selector in selectors:
            found = element.select_one(selector)
            if found:
                return found.get_text(strip=True)
        return ""
    
    def _extract_date(self, element, selectors: List[str]) -> Optional[datetime]:
        """Extract and parse date from element"""
        date_text = self._extract_text(element, selectors)
        if not date_text:
            return None
        
        # Try to parse various date formats
        date_formats = [
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", 
            "%d-%m-%Y", "%Y/%m/%d", "%B %d, %Y"
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_text[:10], fmt)
            except:
                continue
        
        return None
    
    def _contains_relevant_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains relevant keywords"""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)

class ActuarialTenderMonitor:
    """Main monitoring system for actuarial tender opportunities"""
    
    def __init__(self, api_key: str, data_dir: str = "tender_data"):
        self.analyzer = ActuarialTenderAnalyzer(api_key)
        self.scraper = TenderScraper()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Load monitoring sites
        self.tender_sites = self._load_tender_sites()
        
        # Service keywords
        self.primary_keywords = [
            "IFRS 17", "actuarial services", "risk management", "pension consulting",
            "asset liability matching", "enterprise risk management", "Insurance Advisory", "ESG Consulting"
        ]
        
        self.extended_keywords = [
            "Financial and Regulatory Affairs", "Regulatory Policy and Strategy", 
            "Regulatory Compliance", "Liaison with Regulators", "Mergers, Demergers and Acquisitions",
            "Entry into New Markets", "Corporate Governance and Training", "Market Surveys",
            "Enterprise Risk Management", "Enterprise Risk Management Framework Gap Analysis",
            "Quantification of Risk including Risk Modelling", "Risk Appetite", 
            "Risk based Capital Management", "Actuarial Services", "Financial Condition Reports",
            "Product Development", "Embedded value calculation", "Capital Management Report",
            "Investment Policy Statement", "Pension Consulting", "Financial Reporting",
            "Insurance Regulation", "Actuarial Analysis", "Stress Testing", 
            "Sustainability Consulting", "Governance, Risk & Compliance", "Data Protection and Privacy",
            "Pension Scheme Design", "Actuarial Valuation", "Claims Management",
            "Reinsurance Consulting", "Underwriting Solutions", "Insurance Product Design",
            "Reserving Methodology", "Risk Assessment Tools", "Healthcare Actuarial Consulting",
            "Investment Consulting", "Pension Fund Management", "Retirement Solutions",
            "Actuarial Audit", "Compliance Audit", "Statutory Reporting"
        ]
        
        self.all_keywords = self.primary_keywords + self.extended_keywords
    
    def _load_tender_sites(self) -> List[TenderSite]:
        """Load tender sites for monitoring"""
        sites = [
            # International Organizations
            TenderSite(
                url="https://www.ungm.org/Public/Notice",
                name="UN Global Marketplace",
                country="International",
                sector="international",
                search_params={"category": "financial_services"}
            ),
            TenderSite(
                url="https://projects.worldbank.org/procurement",
                name="World Bank eProcurement",
                country="International",
                sector="development",
                search_params={"sector": "financial"}
            ),
            TenderSite(
                url="https://ted.europa.eu/udl",
                name="TED Europa",
                country="EU",
                sector="government",
                search_params={"cpv": "financial_services"}
            ),
            
            # Regional Sites (African focus based on your list)
            TenderSite(
                url="https://www.africagateway.org/",
                name="Africa Gateway",
                country="Africa",
                sector="regional",
                search_params={}
            ),
            TenderSite(
                url="https://www.ppip.go.ke/",
                name="PPIP Kenya",
                country="Kenya", 
                sector="government",
                search_params={}
            ),
            
            # Other Major Procurement Sites
            TenderSite(
                url="https://www.contractsfinder.service.gov.uk/",
                name="UK Contracts Finder",
                country="UK",
                sector="government",
                search_params={"category": "professional_services"}
            ),
            TenderSite(
                url="https://www.merx.com/",
                name="Merx Canada",
                country="Canada",
                sector="mixed",
                search_params={"category": "consulting"}
            )
        ]
        
        return sites
    
    def monitor_all_sites(self) -> List[TenderOpportunity]:
        """Monitor all sites for tender opportunities"""
        all_opportunities = []
        
        logger.info(f"Starting tender monitoring across {len(self.tender_sites)} sites...")
        
        for site in self.tender_sites:
            if not site.active:
                continue
                
            logger.info(f"Monitoring {site.name}...")
            
            try:
                opportunities = self.scraper.scrape_tender_site(site, self.all_keywords)
                
                # Analyze each opportunity with AI
                for opportunity in opportunities:
                    score, service_areas, analysis = self.analyzer.analyze_tender(
                        opportunity.description + " " + opportunity.title,
                        opportunity.title,
                        opportunity.url
                    )
                    
                    opportunity.opportunity_score = score
                    opportunity.service_areas_matched = service_areas
                    opportunity.ai_analysis = analysis
                    opportunity.keywords_matched = self.analyzer._find_keywords(
                        opportunity.title + " " + opportunity.description
                    )
                
                # Filter for relevant opportunities (Medium+ score)
                relevant_opportunities = [
                    opp for opp in opportunities 
                    if opp.opportunity_score in [OpportunityScore.HIGH, OpportunityScore.MEDIUM]
                ]
                
                all_opportunities.extend(relevant_opportunities)
                
                # Update last checked
                site.last_checked = datetime.now()
                
                logger.info(f"Found {len(relevant_opportunities)} relevant opportunities from {site.name}")
                
            except Exception as e:
                logger.error(f"Error monitoring {site.name}: {str(e)}")
        
        # Save opportunities
        for opp in all_opportunities:
            self._save_opportunity(opp)
        
        logger.info(f"Total relevant opportunities found: {len(all_opportunities)}")
        return all_opportunities
    
    def _save_opportunity(self, opportunity: TenderOpportunity):
        """Save opportunity to file"""
        filename = f"{opportunity.timestamp.strftime('%Y%m%d')}_{opportunity.tender_id.replace('/', '_')}.json"
        filepath = self.data_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(asdict(opportunity), f, indent=2, default=str)
    
    def generate_leads_report(self, days_back: int = 7) -> str:
        """Generate business development leads report"""
        
        # Load recent opportunities
        opportunities = self._load_recent_opportunities(days_back)
        
        if not opportunities:
            return "No tender opportunities found in the specified period."
        
        # Sort by opportunity score and closing date
        high_priority = [opp for opp in opportunities if opp.opportunity_score == OpportunityScore.HIGH]
        medium_priority = [opp for opp in opportunities if opp.opportunity_score == OpportunityScore.MEDIUM]
        
        # Group by service area
        service_breakdown = {}
        for opp in opportunities:
            for service_area in opp.service_areas_matched:
                if service_area not in service_breakdown:
                    service_breakdown[service_area] = []
                service_breakdown[service_area].append(opp)
        
        # Generate report
        report = f"""# Actuarial Tender Opportunities Report
**Period:** Last {days_back} days
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Executive Summary
- **Total Opportunities Identified:** {len(opportunities)}
- **High Priority:** {len(high_priority)}
- **Medium Priority:** {len(medium_priority)}
- **Geographic Coverage:** {len(set(opp.location for opp in opportunities))} locations

## High Priority Opportunities
"""
        
        for i, opp in enumerate(high_priority[:10], 1):
            closing_info = f"Closes: {opp.closing_date.strftime('%Y-%m-%d')}" if opp.closing_date else "Closing date TBD"
            value_info = f"Value: {opp.estimated_value}" if opp.estimated_value else "Value: Not specified"
            
            report += f"""
### {i}. {opp.title}
**Client:** {opp.client_organization}  
**Location:** {opp.location}  
**{closing_info}**  
**{value_info}**  
**Service Areas:** {', '.join([area.value.replace('_', ' ').title() for area in opp.service_areas_matched])}

**AI Analysis:** {opp.ai_analysis[:300]}...

**URL:** {opp.url}

---
"""
        
        report += "\n## Service Area Breakdown\n"
        for service_area, opps in service_breakdown.items():
            service_name = service_area.value.replace('_', ' ').title()
            report += f"- **{service_name}:** {len(opps)} opportunities\n"
        
        report += "\n## Medium Priority Opportunities\n"
        for opp in medium_priority[:5]:
            report += f"- **{opp.title}** ({opp.client_organization}) - {opp.location}\n"
        
        return report
    
    def _load_recent_opportunities(self, days_back: int) -> List[TenderOpportunity]:
        """Load opportunities from recent days"""
        opportunities = []
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        for day in range(days_back + 1):
            check_date = start_date + timedelta(days=day)
            date_str = check_date.strftime('%Y%m%d')
            
            for file_path in self.data_dir.glob(f"{date_str}_*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        
                        # Convert enums and dates back
                        data['status'] = TenderStatus(data['status'])
                        data['opportunity_score'] = OpportunityScore(data['opportunity_score'])
                        data['service_areas_matched'] = [ServiceArea(sa) for sa in data['service_areas_matched']]
                        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                        
                        if data.get('closing_date'):
                            data['closing_date'] = datetime.fromisoformat(data['closing_date'])
                        if data.get('publication_date'):
                            data['publication_date'] = datetime.fromisoformat(data['publication_date'])
                        
                        opportunities.append(TenderOpportunity(**data))
                        
                except Exception as e:
                    logger.error(f"Error loading opportunity {file_path}: {str(e)}")
        
        return opportunities

# Business Development utilities
def setup_tender_monitoring():
    """Setup the tender monitoring system"""
    load_dotenv(override=True)
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
    
    return ActuarialTenderMonitor(api_key)

def run_daily_tender_scan():
    """Daily tender scanning routine"""
    monitor = setup_tender_monitoring()
    
    print("Starting daily tender scan...")
    opportunities = monitor.monitor_all_sites()
    
    # Generate leads report
    leads_report = monitor.generate_leads_report()
    
    # Save daily report
    report_filename = f"daily_leads_report_{datetime.now().strftime('%Y%m%d')}.md"
    with open(report_filename, 'w') as f:
        f.write(leads_report)
    
    print(f"Scan complete. Found {len(opportunities)} opportunities.")
    print(f"Report saved to {report_filename}")
    
    return opportunities, leads_report

if __name__ == "__main__":
    # Demo usage
    print("Actuarial Tender Intelligence Platform")
    print("="*50)
    
    try:
        opportunities, report = run_daily_tender_scan()
        print("\nSample opportunities found:")
        
        for i, opp in enumerate(opportunities[:3], 1):
            print(f"{i}. {opp.title} - {opp.opportunity_score.value} priority")
            
    except Exception as e:
        print(f"Demo failed: {str(e)}")
        print("Please ensure your .env file contains a valid OPENAI_API_KEY")
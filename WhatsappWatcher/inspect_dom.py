"""
WhatsApp Web DOM Inspector

This script inspects the WhatsApp Web DOM structure to identify correct selectors
for chat list, messages, and unread indicators.

Usage:
    1. First, run the main WhatsApp watcher to log in
    2. Then run this script to inspect the DOM
    3. Review the output to update selectors in check_for_updates.py
"""

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import time
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

def inspect_whatsapp_dom():
    """Inspect WhatsApp Web DOM structure."""
    
    session_path = Path(os.getenv('WHATSAPP_SESSION_PATH', Path.home() / '.digital_fte' / 'sessions' / 'whatsapp'))
    session_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("WhatsApp Web DOM Inspector")
    print("=" * 70)
    print(f"\nSession path: {session_path}")
    print("\nThis script will:")
    print("1. Open WhatsApp Web")
    print("2. Wait for you to log in (if needed)")
    print("3. Inspect the DOM structure")
    print("4. Output all relevant selectors\n")
    
    playwright = sync_playwright().start()
    
    # Launch browser
    browser_context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(session_path),
        headless=False,  # Must be visible for inspection
        args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
        ]
    )
    
    page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
    page.set_viewport_size({"width": 1280, "height": 720})
    
    # Navigate to WhatsApp
    print("Navigating to WhatsApp Web...")
    page.goto('https://web.whatsapp.com', wait_until='networkidle')
    
    # Wait for login
    print("\n⏳ Waiting for login...")
    print("If QR code is shown, please scan it with your phone.")
    print("Waiting up to 120 seconds for chat list to appear...\n")
    
    try:
        page.wait_for_selector('[data-testid="chat-list"], [role="list"]', timeout=120000)
        print("✅ Chat list detected - you're logged in!")
    except Exception:
        print("❌ Login timeout. Please restart and scan QR code.")
        browser_context.close()
        playwright.stop()
        return
    
    # Give it time to fully load
    time.sleep(5)
    
    # Start inspection
    print("\n" + "=" * 70)
    print("DOM INSPECTION RESULTS")
    print("=" * 70)
    
    # 1. Overall page structure
    print("\n### 1. PAGE STRUCTURE ###\n")
    
    page_structure = page.evaluate("""() => {
        const info = {
            url: window.location.href,
            title: document.title,
            body_classes: document.body.className,
            root_elements: []
        };
        
        // Get root level elements
        const root = document.querySelector('#app, #main, [data-testid="main"]');
        if (root) {
            info.root_elements.push({
                tag: root.tagName,
                id: root.id,
                class: root.className,
                data_testid: root.getAttribute('data-testid'),
                children_count: root.children.length
            });
        }
        
        return info;
    }""")
    
    print(f"URL: {page_structure['url']}")
    print(f"Title: {page_structure['title']}")
    print(f"Body classes: {page_structure['body_classes']}")
    print(f"Root elements: {json.dumps(page_structure['root_elements'], indent=2)}")
    
    # 2. Chat list panel
    print("\n### 2. CHAT LIST PANEL ###\n")
    
    chat_list_info = page.evaluate("""() => {
        const results = [];
        
        // Try different selectors for chat list
        const selectors = [
            '[data-testid="chat-list"]',
            '[role="list"]',
            '[data-asset-testid="chat-list"]',
            '#pane-side',
            '[data-testid="chat-list-panel"]'
        ];
        
        selectors.forEach(selector => {
            const el = document.querySelector(selector);
            if (el) {
                results.push({
                    selector: selector,
                    found: true,
                    tag: el.tagName,
                    id: el.id,
                    class: el.className,
                    data_testid: el.getAttribute('data-testid'),
                    role: el.getAttribute('role'),
                    children_count: el.children.length,
                    aria_label: el.getAttribute('aria-label'),
                    all_attributes: Array.from(el.attributes).map(a => `${a.name}="${a.value}"`).join(' ')
                });
            }
        });
        
        return results;
    }""")
    
    for item in chat_list_info:
        print(f"✅ Found: {item['selector']}")
        print(f"Tag: {item['tag']}, Role: {item['role']}")
        print(f"Class: {item['class']}")
        print(f"Data-testid: {item['data_testid']}")
        print(f"Children: {item['children_count']}")
        print(f"Aria-label: {item['aria_label']}")
        print()
    
    # 3. Chat items
    print("\n### 3. CHAT ITEMS (Individual Chats) ###\n")
    
    chat_items_info = page.evaluate("""() => {
        const results = [];
        
        // Find chat list container first
        const chatList = document.querySelector('[data-testid="chat-list"], [role="list"], #pane-side');
        if (!chatList) return results;
        
        // Get first 5 chat items
        const chatItems = chatList.querySelectorAll('[role="listitem"], [data-testid="chat-item"], div[role="listitem"]');
        
        chatItems.forEach((item, idx) => {
            if (idx >= 5) return;
            
            results.push({
                index: idx,
                tag: item.tagName,
                id: item.id,
                class: item.className,
                data_testid: item.getAttribute('data-testid'),
                role: item.getAttribute('role'),
                aria_label: item.getAttribute('aria-label'),
                all_attributes: Array.from(item.attributes).map(a => `${a.name}="${a.value}"`).join(' ')
            });
        });
        
        return results;
    }""")
    
    for item in chat_items_info:
        print(f"Chat Item {item['index']}:")
        print(f"   Role: {item['role']}")
        print(f"   Class: {item['class']}")
        print(f"   Data-testid: {item['data_testid']}")
        print(f"   Aria-label: {item['aria_label']}")
        print()
    
    # 4. Unread indicators
    print("\n### 4. UNREAD INDICATORS ###\n")
    
    unread_info = page.evaluate("""() => {
        const results = [];
        
        // Look for unread indicators
        const selectors = [
            '[aria-label*="unread"]',
            '[data-testid="unread-marker"]',
            'span[class*="unread"]',
            'div[class*="unread"]',
            'span[class*="_ac3b"]',
            'span[class*="iuthp"]',
            'span[class*="Ep61I"]'  // Common WhatsApp class pattern
        ];
        
        selectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                elements.forEach((el, idx) => {
                    if (idx >= 3) return;  // Limit per selector
                    
                    results.push({
                        selector: selector,
                        tag: el.tagName,
                        class: el.className,
                        text: el.innerText?.trim() || '',
                        aria_label: el.getAttribute('aria-label'),
                        parent_class: el.parentElement?.className,
                        all_attributes: Array.from(el.attributes).map(a => `${a.name}="${a.value}"`).join(' ')
                    });
                });
            }
        });
        
        return results;
    }""")
    
    if unread_info:
        for item in unread_info:
            print(f"✅ Unread indicator found:")
            print(f"   Selector: {item['selector']}")
            print(f"   Tag: {item['tag']}, Class: {item['class']}")
            print(f"   Text: {item['text']}")
            print(f"   Aria-label: {item['aria_label']}")
            print(f"   Parent class: {item['parent_class']}")
            print()
    else:
        print("No unread indicators found with common selectors.")
        print("Looking for green badges numerically...")
        
        # Alternative: look for any span with numbers
        alt_unread = page.evaluate("""() => {
            const results = [];
            const spans = document.querySelectorAll('span');
            
            spans.forEach(span => {
                const text = span.innerText?.trim();
                if (text && /^\\d+$/.test(text) && parseInt(text) > 0 && parseInt(text) < 1000) {
                    results.push({
                        text: text,
                        class: span.className,
                        aria_label: span.getAttribute('aria-label'),
                        parent_class: span.parentElement?.className,
                        all_attributes: Array.from(span.attributes).map(a => `${a.name}="${a.value}"`).join(' ')
                    });
                }
            });
            
            return results.slice(0, 10);
        }""")
        
        for item in alt_unread:
            print(f"   Number badge: {item['text']}, Class: {item['class']}, Aria: {item['aria_label']}")
    
    # 5. Message preview text
    print("\n### 5. MESSAGE PREVIEW TEXT ###\n")
    
    message_preview_info = page.evaluate("""() => {
        const results = [];
        
        // Look for message preview selectors
        const selectors = [
            'span[data-testid="message-preview"]',
            'span[data-testid="last-message"]',
            'div[data-testid="chat-list-message"]',
            'span[dir="auto"]',
            'span[class*="message"]'
        ];
        
        selectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                elements.forEach((el, idx) => {
                    if (idx >= 3) return;
                    
                    results.push({
                        selector: selector,
                        text: el.innerText?.trim() || '',
                        class: el.className,
                        aria_label: el.getAttribute('aria-label'),
                        parent_class: el.parentElement?.className
                    });
                });
            }
        });
        
        return results;
    }""")
    
    for item in message_preview_info:
        print(f"Message preview:")
        print(f"   Selector: {item['selector']}")
        print(f"   Text: {item['text'][:80]}...")
        print(f"   Class: {item['class']}")
        print(f"   Aria: {item['aria_label']}")
        print()
    
    # 6. Chat name extraction
    print("\n### 6. CHAT NAME/CONTACT EXTRACTION ###\n")
    
    chat_name_info = page.evaluate("""() => {
        const results = [];
        
        const chatList = document.querySelector('[data-testid="chat-list"], [role="list"]');
        if (!chatList) return results;
        
        const chatItems = chatList.querySelectorAll('[role="listitem"]');
        
        chatItems.forEach((item, idx) => {
            if (idx >= 5) return;
            
            // Look for chat name
            const nameEl = item.querySelector('span[title], [aria-label], h1, h2, h3, div[class*="title"]');
            const name = nameEl ? (nameEl.getAttribute('title') || nameEl.getAttribute('aria-label') || nameEl.innerText?.trim()) : null;
            
            results.push({
                chat_index: idx,
                name: name,
                name_element: nameEl ? {
                    tag: nameEl.tagName,
                    class: nameEl.className,
                    title: nameEl.getAttribute('title'),
                    aria: nameEl.getAttribute('aria-label')
                } : null
            });
        });
        
        return results;
    }""")
    
    for item in chat_name_info:
        print(f"Chat {item['chat_index']}:")
        print(f"   Name: {item['name']}")
        if item['name_element']:
            print(f"   Name element: {json.dumps(item['name_element'], indent=6)}")
        print()
    
    # 7. Complete chat item structure
    print("\n### 7. COMPLETE CHAT ITEM STRUCTURE (First 3 chats) ###\n")
    
    complete_structure = page.evaluate("""() => {
        const results = [];
        
        const chatList = document.querySelector('[data-testid="chat-list"], [role="list"]');
        if (!chatList) return results;
        
        const chatItems = chatList.querySelectorAll('[role="listitem"]');
        
        chatItems.forEach((item, idx) => {
            if (idx >= 3) return;
            
            // Get all child elements with their structure
            const structure = {
                chat_aria: item.getAttribute('aria-label'),
                children: []
            };
            
            const children = item.children;
            for (let child of children) {
                structure.children.push({
                    tag: child.tagName,
                    class: child.className,
                    role: child.getAttribute('role'),
                    data_testid: child.getAttribute('data-testid'),
                    aria_label: child.getAttribute('aria-label'),
                    text: child.innerText?.trim().substring(0, 50) || '',
                    children_count: child.children.length
                });
            }
            
            results.push(structure);
        });
        
        return results;
    }""")
    
    for idx, structure in enumerate(complete_structure):
        print(f"Chat {idx} structure:")
        print(f"   Aria-label: {structure['chat_aria']}")
        print(f"   Children ({len(structure['children'])}):")
        for child in structure['children']:
            print(f"      - {child['tag']}: role={child['role']}, testid={child['data_testid']}")
            print(f"        class={child['class'][:100] if child['class'] else 'None'}...")
            print(f"        text={child['text'][:50]}...")
        print()
    
    # 8. Mutation Observer test
    print("\n### 8. SETTING UP MUTATION OBSERVER FOR REAL-TIME TESTING ###\n")
    
    # Set up mutation observer to detect new messages
    page.evaluate("""() => {
        window.whatsappMutationLog = [];
        
        const observer = new MutationObserver((mutations) => {
            mutations.forEach(mutation => {
                if (mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1) {  // Element node
                            const info = {
                                type: 'added',
                                tag: node.tagName,
                                class: node.className,
                                text: node.innerText?.substring(0, 100) || '',
                                time: new Date().toISOString()
                            };
                            window.whatsappMutationLog.push(info);
                        }
                    });
                }
                
                if (mutation.type === 'attributes') {
                    const info = {
                        type: 'attribute_change',
                        tag: mutation.target.tagName,
                        class: mutation.target.className,
                        attribute: mutation.attributeName,
                        time: new Date().toISOString()
                    };
                    window.whatsappMutationLog.push(info);
                }
            });
        });
        
        const chatList = document.querySelector('[data-testid="chat-list"], [role="list"]');
        if (chatList) {
            observer.observe(chatList, {
                childList: true,
                subtree: true,
                attributes: true,
                characterData: true
            });
            
            console.log('MutationObserver attached to chat list');
        }
    }""")
    
    print("✅ MutationObserver attached to chat list.")
    print("   Send a test message to your WhatsApp from another device.")
    print("   Wait 10 seconds, then we'll check what changed...\n")
    
    time.sleep(10)
    
    # Check mutation log
    mutation_log = page.evaluate("""() => {
        return window.whatsappMutationLog || [];
    }""")
    
    if mutation_log:
        print(f"📊 Detected {len(mutation_log)} mutations:")
        for entry in mutation_log[:20]:  # Show first 20
            print(f"   [{entry['type']}] {entry['tag']}.{entry['class'][:50] if entry['class'] else 'no-class'} - {entry.get('text', '')[:50]}")
    else:
        print("No mutations detected in the last 10 seconds.")
    
    # 9. Export all selectors to JSON
    print("\n### 9. EXPORTING SELECTORS TO JSON ###\n")
    
    all_selectors = page.evaluate("""() => {
        const selectors = {
            chat_list: [],
            chat_items: [],
            unread_indicators: [],
            message_previews: [],
            chat_names: [],
            timestamps: []
        };
        
        // Chat list
        document.querySelectorAll('[data-testid="chat-list"], [role="list"], #pane-side').forEach(el => {
            selectors.chat_list.push({
                selector: `[data-testid="${el.getAttribute('data-testid')}"]`,
                role: el.getAttribute('role'),
                class: el.className
            });
        });
        
        // Chat items
        document.querySelectorAll('[role="listitem"]').forEach((el, idx) => {
            if (idx < 10) {
                selectors.chat_items.push({
                    selector: `[role="listitem"]:nth-child(${idx + 1})`,
                    class: el.className,
                    aria: el.getAttribute('aria-label')
                });
            }
        });
        
        // Unread indicators
        document.querySelectorAll('[aria-label*="unread"], [data-testid*="unread"], span[class*="_ac3b"]').forEach(el => {
            selectors.unread_indicators.push({
                selector: `[aria-label*="unread"]`,
                class: el.className,
                text: el.innerText
            });
        });
        
        // Message previews
        document.querySelectorAll('span[data-testid="message-preview"], span[dir="auto"]').forEach((el, idx) => {
            if (idx < 10) {
                selectors.message_previews.push({
                    selector: `span[data-testid="message-preview"]`,
                    text: el.innerText?.substring(0, 100),
                    class: el.className
                });
            }
        });
        
        // Chat names
        document.querySelectorAll('span[title]').forEach((el, idx) => {
            if (idx < 10) {
                selectors.chat_names.push({
                    selector: `span[title]`,
                    title: el.getAttribute('title'),
                    class: el.className
                });
            }
        });
        
        // Timestamps
        document.querySelectorAll('span[dir="auto"]').forEach((el, idx) => {
            const text = el.innerText?.trim();
            if (text && (':' in text || 'AM' in text || 'PM' in text)) {
                selectors.timestamps.push({
                    text: text,
                    class: el.className
                });
            }
        });
        
        return selectors;
    }""")
    
    output_file = Path(__file__).parent / 'whatsapp_selectors.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_selectors, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Selectors exported to: {output_file}")
    print(f"\nJSON structure:")
    print(json.dumps(all_selectors, indent=2)[:2000] + "...")
    
    # Cleanup
    print("\n" + "=" * 70)
    print("Inspection complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Review the selectors above")
    print("2. Check whatsapp_selectors.json for detailed output")
    print("3. Update check_for_updates.py with correct selectors")
    print("\nKeeping browser open for manual inspection. Close it to exit.\n")
    
    # Keep browser open for manual inspection
    try:
        input("Press Enter to close browser and exit...")
    except:
        pass
    
    browser_context.close()
    playwright.stop()
    print("Browser closed.")


if __name__ == "__main__":
    inspect_whatsapp_dom()

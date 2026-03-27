from typing import List , Dict , Any

def CheckForUpdates(self) -> List[Dict[str, Any]]:
        """
        Check Gmail for new unread messages.
        
        Returns:
            List of message dictionaries with id, snippet, headers
        """
        if not self.service:
            if not self._authenticate():
                return []
        
        try:
            # Build query for unread, important messages
            query = 'is:unread'
            if 'IMPORTANT' in self.label_ids:
                query += ' is:important'
            
            # Fetch messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=10  # Limit to 10 at a time
            ).execute()
            
            messages = results.get('messages', [])
            
            # Filter out already processed
            new_messages = []
            for msg in messages:
                msg_id = msg['id']
                if msg_id not in self.processed_ids:
                    # Fetch full message
                    full_msg = self.service.users().messages().get(
                        userId='me',
                        id=msg_id,
                        format='metadata',
                        metadataHeaders=['From', 'To', 'Subject', 'Date']
                    ).execute()
                    
                    new_messages.append({
                        'id': msg_id,
                        'snippet': full_msg.get('snippet', ''),
                        'headers': {
                            h['name']: h['value']
                            for h in full_msg['payload']['headers']
                        }
                    })
            
            return new_messages
            
        except Exception as e:
            self.logger.error(f"Error checking Gmail: {e}")
            return []
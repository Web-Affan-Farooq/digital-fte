def MarkAsRead(self, message_id: str) -> bool:
    """
    Mark a Gmail message as read.
    
    Args:
        message_id: Gmail message ID
        
    Returns:
        True if successful, False otherwise
    """
    if not self.service:
        if not self._authenticate():
            return False
    
    try:
        self.service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        self.logger.debug(f"Marked message {message_id} as read")
        return True
    except Exception as e:
        self.logger.error(f"Could not mark message as read: {e}")
        return False
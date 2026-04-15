# Placeholder for post-request summary generation task. This will be implemented in a future update.

TOKEN_THRESHOLD = 100_000

# The implementation will involve:
# Get the HistoryCompactorService
# Get the SummaryService
# Get the MessageService

# def post_request_summary_task(conversation_id: UUID):
#     # Get the conversation summary
#     # Get the list of messages by conversation_id where message.created_at is > summary.window_end
#     # Batch process the list of messages and keep a running token count
#     # If the token count exceeds the threshold, pass the existing summary + the batch of messages to the HistoryCompactorService to generate a new summary
#       # Update the summary with the new content and token count, and set the window_start and window_end to the created_at of the last message in the batch
#     # Else update the window_end of the existing summary to the created_at of the last message in the batch

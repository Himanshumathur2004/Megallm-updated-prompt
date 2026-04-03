"""Pipeline webhook routes for handling workflow completion events."""
from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger('api')

pipeline_bp = Blueprint('pipeline', __name__, url_prefix='/api/pipeline')


@pipeline_bp.route('/run-complete', methods=['POST', 'OPTIONS'])
def handle_pipeline_complete():
    """
    Webhook endpoint for receiving pipeline completion notifications.
    
    Expected POST payload:
    {
        "workflow_id": "string",
        "account_id": "string",
        "status": "completed" | "failed",
        "result": {
            "blogs": [list of blog IDs],
            "error": "error message if status is failed"
        }
    }
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        workflow_id = data.get('workflow_id')
        account_id = data.get('account_id')
        status = data.get('status')
        result = data.get('result', {})
        
        if not all([workflow_id, account_id, status]):
            return jsonify({"error": "Missing required fields: workflow_id, account_id, status"}), 400
        
        logger.info(f"Received pipeline completion: workflow_id={workflow_id}, "
                   f"account_id={account_id}, status={status}")
        
        if status == 'completed':
            blogs = result.get('blogs', [])
            logger.info(f"Pipeline {workflow_id} completed with {len(blogs)} blogs")
            return jsonify({
                "success": True,
                "message": f"Pipeline {workflow_id} processed successfully",
                "blogs_count": len(blogs)
            }), 200
        
        elif status == 'failed':
            error = result.get('error', 'Unknown error')
            logger.error(f"Pipeline {workflow_id} failed: {error}")
            return jsonify({
                "success": False,
                "message": f"Pipeline {workflow_id} failed",
                "error": error
            }), 200
        
        else:
            return jsonify({"error": f"Invalid status: {status}"}), 400
    
    except Exception as e:
        logger.exception(f"Error processing pipeline completion webhook")
        return jsonify({"error": str(e)}), 500

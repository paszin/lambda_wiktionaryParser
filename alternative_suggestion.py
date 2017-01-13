# -*- coding: utf-8 -*-

import json
try:
    import boto3
except:
    pass ## not important for local development

class DynamoDBConnector:

    def  __init__(self):
        dynamodb = boto3.resource('dynamodb')
        self.table = dynamodb.Table('Dictionary')


    def update(self, word, alternative, explanation):
        item = self.table.get_item(
            Key={
            'word': word
            },
            AttributesToGet=['word','alternatives']).get("Item")
        if not item.get("word"):
            raise ValueError(word + "is not in database")
        alts = item.get("alternatives")
        if not alts:
            self.table.update_item(Key={"word": word}, UpdateExpression="set alternatives = :r",
                ExpressionAttributeValues={
                    ':r': [],
                })
        result = self.table.update_item(
            Key={
            'word': word
            },
            UpdateExpression="SET alternatives = list_append(alternatives, :i)",
            ExpressionAttributeValues={
                ':i': [{"ipa": alternative, "explanation": explanation}],
            },
            ReturnValues="UPDATED_NEW"
            )
        if result['ResponseMetadata']['HTTPStatusCode'] == 200 and 'Attributes' in result:
            return result['Attributes']['alternatives']



def lambda_handler(event, context):
    word = event.get("word")
    alternative = event.get("ipa")
    explanation = event.get("explanation")
    if not word or not alternative:
        return {"error": "please provide word and ipa"}
    word = word.strip()
    db = DynamoDBConnector()
    try:
        result = db.update(word, alternative, explanation)
    except ValueError:
        return "word not in database"
    finally:
        return result

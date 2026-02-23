# contains the random combination of variables for the personas used in synthetic data generation
import config
import random


# demographics
genders = ['male', 'female', 'transgender woman', 'transgender man', 'non-binary']
occupations = ['software engineer', 'teacher', 'nurse', 'artist', 'salesperson', 
               'retired', 'student', 'unemployed', 'entrepreneur', 'stay-at-home parent']

# presenting issues
presenting_issues = ['anxiety', 'depression', 'relationship issues', 'work stress', 
                    'grief', 'self-esteem issues', 'sexuality issues', 'trauma', 'substance abuse', 
                    'eating disorders', 'chronic illness', 'gender dysphoria', 'identity issues', 
                    'family conflict', 'life transitions', 'body dysmorphia', 'obsessive-compulsive disorder', 
                    'phobias', 'sleep disorders', 'anger management issues']

# romantic relationship status
relationship_statuses = ['single', 'in a relationship', 'married', 'divorced', 'widowed']

# living situation
living_situations = ['living alone', 'living with family', 'living with roommates', 'living with partner', 'living in a group home', 'living in a shelter']

# therapy modalities
therapy_modalities = ['cognitive-behavioral therapy', 'psychodynamic therapy', 'humanistic therapy', 
                     'integrative therapy', 'mindfulness-based therapy', 'art therapy', 
                     'dialectical behavior therapy', 'acceptance and commitment therapy', 
                     'eye movement desensitization and reprocessing (EMDR)', 'exposure therapy']

# patient speaking styles
speaking_styles = ['verbose', 'concise', 'emotional', 'logical', 'intellectualizing', 'narrative', 
                   'disorganized', 'rambling', 'focused', 'tangential', 'metaphorical', 'literal']

# therapist speaking styles
therapist_speaking_styles = ['empathetic', 'direct', 'analytical', 'supportive', 'challenging', 
                             'reflective', 'encouraging', 'neutral', 'collaborative', 'authoritative',
                             'offensive', 'dismissive', 'condescending', 'patronizing', 'invalidating']


def generate_random_fingerprint():
    fingerprint = {
        'age': random.randint(18, 75),
        'gender': random.choice(genders),
        'occupation': random.choice(occupations),
        'presenting_issue': random.choice(presenting_issues),
        'relationship_status': random.choice(relationship_statuses),
        'living_situation': random.choice(living_situations),
        'therapy_modality': random.choice(therapy_modalities),
        'patient_speaking_style': random.choice(speaking_styles),
        'therapist_speaking_style': random.choice(therapist_speaking_styles),
        'sessions': random.randint(1, 20),
        'conversation_length': random.randint(config.CONVERSATION_LENGTH_MIN, config.CONVERSATION_LENGTH_MAX)
    }

    return fingerprint

if __name__ == "__main__":
    # generate and print a random fingerprint for testing
    random_fingerprint = generate_random_fingerprint()
    print(random_fingerprint)

$name = "tacmed-rag-v2"
$region = "eu-central-1"
$user = "arn:aws:iam::168705873426:user/roman-dev"
$role = "arn:aws:iam::168705873426:role/TacMed_KB_Role"

# Policies
aws opensearchserverless create-security-policy --name "$name-enc" --type encryption --policy "{\"Rules\":[{\"ResourceType\":\"collection\",\"Resource\":[\"collection/$name\"]}],\"AWSOwnedKey\":true}" --region $region
aws opensearchserverless create-security-policy --name "$name-net" --type network --policy "[{\"Rules\":[{\"ResourceType\":\"collection\",\"Resource\":[\"collection/$name\"]},{\"ResourceType\":\"dashboard\",\"Resource\":[\"collection/$name\"]}],\"AllowFromPublic\":true}]" --region $region
aws opensearchserverless create-access-policy --name "$name-access" --type data --policy "[{\"Rules\":[{\"ResourceType\":\"collection\",\"Resource\":[\"collection/$name\"],\"Permission\":[\"aoss:*\"]},{\"ResourceType\":\"index\",\"Resource\":[\"index/$name/*\"],\"Permission\":[\"aoss:*\"]}],\"Principal\":[\"$user\",\"$role\"]}]" --region $region

# Collection
aws opensearchserverless create-collection --name $name --type VECTORSEARCH --region $region

export type BirdProfile = {
  species: string;
  scientificName: string;
  family: string;
  order: string;
  status: string;
  habitat: string;
  diet: string;
  size: string;
  region: string;
  image: string;
  description: string;
  datasetSource: "Current model" | "Clean 50 dataset" | "Current model + clean 50 dataset";
  trainingImages: number;
  supportedByCurrentModel: boolean;
  supportedByCleanDataset: boolean;
};

export const currentModelLabels = [
  "ABBOTTS BABBLER",
  "ABBOTTS BOOBY",
  "ABYSSINIAN GROUND HORNBILL",
  "AFRICAN CROWNED CRANE",
  "AFRICAN EMERALD CUCKOO",
  "AFRICAN FIREFINCH",
  "AFRICAN OYSTER CATCHER",
  "ALBATROSS",
  "ALBERTS TOWHEE",
  "ALEXANDRINE PARAKEET",
  "AMERICAN DIPPER",
  "AMERICAN ROBIN",
  "ASIAN GREEN BEE EATER",
  "BALD EAGLE",
  "BANDED BROADBILL",
  "BARN SWALLOW",
  "BLACK BAZA",
  "BLUE GRAY GNATCATCHER",
  "BLUE THROATED PIPING GUAN",
  "CAMPO FLICKER",
  "CASPIAN TERN",
  "COPPERSMITH BARBET",
  "CRESTED WOOD PARTRIDGE",
  "CRIMSON SUNBIRD",
  "D-ARNAUDS BARBET",
  "DARK EYED JUNCO",
  "EASTERN YELLOW ROBIN",
  "EUROPEAN STARLING",
  "FRILL BACK PIGEON",
  "GOLDEN EAGLE",
  "GREAT BLUE HERON",
  "GREATER PRAIRIE CHICKEN",
  "GREY HEADED CHACHALACA",
  "HOUSE FINCH",
  "HOUSE SPARROW",
  "JACOBIN PIGEON",
  "KNOB BILLED DUCK",
  "LAUGHING GULL",
  "LIMPKIN",
  "MALLARD",
  "MARABOU STORK",
  "MERLIN",
  "MILITARY MACAW",
  "MOURNING DOVE",
  "NORTHERN CARDINAL",
  "NORTHERN PARULA",
  "ORNATE HAWK EAGLE",
  "OSPREY",
  "OVENBIRD",
  "OYSTER CATCHER",
  "PYRRHULOXIA",
  "RAZORBILL",
  "RED BEARDED BEE EATER",
  "RED BILLED TROPICBIRD",
  "RED KNOT",
  "RED-SHOULDERED HAWK",
  "RED-TAILED HAWK",
  "ROCK PIGEON",
  "ROSE BREASTED COCKATOO",
  "ROSEATE SPOONBILL",
  "RUFOUS TREPE",
  "SAYS PHOEBE",
  "SNOWY EGRET",
  "SORA",
  "STRIATED CARACARA",
  "SWINHOES PHEASANT",
  "VARIED THRUSH",
  "VIOLET BACKED STARLING",
  "VIOLET GREEN SWALLOW",
  "WILLOW PTARMIGAN",
  "WOOD DUCK",
  "WOOD THRUSH",
  "WOODLAND KINGFISHER",
  "WRENTIT",
  "YELLOW BREASTED CHAT",
] as const;

export const cleanDatasetLabels = [
  "RUFOUS TREPE",
  "HOUSE FINCH",
  "D-ARNAUDS BARBET",
  "OVENBIRD",
  "ASIAN GREEN BEE EATER",
  "SWINHOES PHEASANT",
  "WOOD DUCK",
  "CASPIAN TERN",
  "RED BILLED TROPICBIRD",
  "WOOD THRUSH",
  "FRILL BACK PIGEON",
  "MERLIN",
  "PYRRHULOXIA",
  "MILITARY MACAW",
  "ORNATE HAWK EAGLE",
  "OYSTER CATCHER",
  "LAUGHING GULL",
  "EASTERN YELLOW ROBIN",
  "JACOBIN PIGEON",
  "DARK EYED JUNCO",
  "GREATER PRAIRIE CHICKEN",
  "RED-TAILED HAWK",
  "YELLOW BREASTED CHAT",
  "VIOLET BACKED STARLING",
  "VIOLET GREEN SWALLOW",
  "LIMPKIN",
  "RED KNOT",
  "SORA",
  "GREY HEADED CHACHALACA",
  "BLUE THROATED PIPING GUAN",
  "CRIMSON SUNBIRD",
  "CAMPO FLICKER",
  "CRESTED WOOD PARTRIDGE",
  "KNOB BILLED DUCK",
  "MARABOU STORK",
  "RED BEARDED BEE EATER",
  "ROSE BREASTED COCKATOO",
  "SAYS PHOEBE",
  "COPPERSMITH BARBET",
  "NORTHERN PARULA",
  "STRIATED CARACARA",
  "BLUE GRAY GNATCATCHER",
  "WILLOW PTARMIGAN",
  "BANDED BROADBILL",
  "WOODLAND KINGFISHER",
  "AMERICAN DIPPER",
  "RAZORBILL",
  "ROSEATE SPOONBILL",
  "VARIED THRUSH",
  "WRENTIT",
] as const;

const profileOverrides: Record<string, Partial<BirdProfile>> = {
  "ABBOTTS BABBLER": {
    scientificName: "Malacocincla abbotti",
    family: "Pellorneidae",
    order: "Passeriformes",
    status: "Least Concern",
    habitat: "Dense undergrowth, forest edges, bamboo, and scrubland.",
    diet: "Insects, small invertebrates, and occasional seeds.",
    size: "15-17 cm",
    region: "South and Southeast Asia",
    description: "A shy ground-feeding bird that stays close to thick cover and is often detected by its call.",
  },
  "ABBOTTS BOOBY": {
    scientificName: "Papasula abbotti",
    family: "Sulidae",
    order: "Suliformes",
    status: "Endangered",
    habitat: "Oceanic islands and tropical marine zones.",
    diet: "Fish and squid caught by plunge-diving.",
    size: "79 cm",
    region: "Indian Ocean",
    description: "A rare seabird known for long-distance ocean foraging and nesting on remote island forests.",
  },
  "ABYSSINIAN GROUND HORNBILL": {
    scientificName: "Bucorvus abyssinicus",
    family: "Bucorvidae",
    order: "Bucerotiformes",
    status: "Vulnerable",
    habitat: "Savannas, grasslands, and open woodland.",
    diet: "Reptiles, insects, small mammals, and arachnids.",
    size: "90-100 cm",
    region: "Sub-Saharan Africa",
    description: "A large terrestrial hornbill that walks across open habitat while searching for prey.",
  },
  "AFRICAN CROWNED CRANE": {
    scientificName: "Balearica regulorum",
    family: "Gruidae",
    order: "Gruiformes",
    status: "Endangered",
    habitat: "Wetlands, grasslands, marshes, and cultivated areas.",
    diet: "Seeds, grasses, grains, insects, reptiles, and small mammals.",
    size: "100-110 cm",
    region: "Eastern and Southern Africa",
    description: "A graceful crane with a golden crown, often seen in pairs near wet grassland.",
  },
  "AFRICAN EMERALD CUCKOO": {
    scientificName: "Chrysococcyx cupreus",
    family: "Cuculidae",
    order: "Cuculiformes",
    status: "Least Concern",
    habitat: "Forests, woodland, and leafy gardens.",
    diet: "Caterpillars, ants, and other insects.",
    size: "18-20 cm",
    region: "Sub-Saharan Africa",
    description: "A brightly colored cuckoo that is easier to hear than see in dense tree canopies.",
  },
  "AFRICAN FIREFINCH": {
    scientificName: "Lagonosticta rubricata",
    family: "Estrildidae",
    order: "Passeriformes",
    status: "Least Concern",
    habitat: "Grassland, forest edges, thickets, and gardens.",
    diet: "Grass seeds supplemented with small insects.",
    size: "10-11 cm",
    region: "Africa",
    description: "A small finch with red plumage, usually feeding low in vegetation or on the ground.",
  },
  "BALD EAGLE": {
    scientificName: "Haliaeetus leucocephalus",
    family: "Accipitridae",
    order: "Accipitriformes",
    status: "Least Concern",
    habitat: "Coasts, lakes, rivers, wetlands, and large reservoirs.",
    diet: "Fish, waterbirds, carrion, and small mammals.",
    size: "70-102 cm",
    region: "North America",
    description: "A large sea eagle with a white head and tail, included to improve separation from hawks.",
  },
  "RED-TAILED HAWK": {
    scientificName: "Buteo jamaicensis",
    family: "Accipitridae",
    order: "Accipitriformes",
    status: "Least Concern",
    habitat: "Open country, roadsides, grassland, deserts, woodland edges, and cities.",
    diet: "Small mammals, reptiles, birds, and carrion.",
    size: "45-65 cm",
    region: "North and Central America",
    description: "A broad-winged hawk with a reddish tail in adults, represented in both the active model and clean dataset.",
  },
  "GOLDEN EAGLE": {
    scientificName: "Aquila chrysaetos",
    family: "Accipitridae",
    order: "Accipitriformes",
    status: "Least Concern",
    habitat: "Mountains, cliffs, open country, and grasslands.",
    diet: "Mammals, birds, reptiles, and carrion.",
    size: "66-102 cm",
    region: "Northern Hemisphere",
    description: "A powerful eagle added as a raptor contrast class for better real-world identification.",
  },
  OSPREY: {
    scientificName: "Pandion haliaetus",
    family: "Pandionidae",
    order: "Accipitriformes",
    status: "Least Concern",
    habitat: "Coasts, rivers, lakes, and wetlands.",
    diet: "Mostly fish caught by diving feet-first.",
    size: "50-66 cm",
    region: "Worldwide near water",
    description: "A fish-eating raptor with long angled wings and a dark eye stripe.",
  },
  "BLACK BAZA": {
    scientificName: "Aviceda leuphotes",
    family: "Accipitridae",
    order: "Accipitriformes",
    status: "Least Concern",
    habitat: "Forests, wooded country, plantations, and forest edges.",
    diet: "Large insects, lizards, small birds, and other small animals.",
    size: "30-35 cm",
    region: "South and Southeast Asia",
    trainingImages: 275,
    description: "A compact black-and-white raptor with a short crest, now strengthened with extra real-world training images.",
  },
};

const currentModelSet = new Set<string>(currentModelLabels);
const cleanDatasetSet = new Set<string>(cleanDatasetLabels);

export const birdProfiles: BirdProfile[] = [...new Set([...currentModelLabels, ...cleanDatasetLabels])].map(createBirdProfile);

export const guideDatasetSummary = {
  totalProfiles: birdProfiles.length,
  currentModelClasses: currentModelLabels.length,
  cleanDatasetClasses: cleanDatasetLabels.length,
  cleanDatasetImagesPerClass: 200,
};

export function getBirdProfile(species: string) {
  return findBirdProfile(species) ?? birdProfiles[0];
}

export function findBirdProfile(species: string) {
  const normalized = species.trim().toUpperCase();
  return birdProfiles.find((bird) => bird.species === normalized);
}

function createBirdProfile(species: string): BirdProfile {
  const supportedByCurrentModel = currentModelSet.has(species);
  const supportedByCleanDataset = cleanDatasetSet.has(species);
  const source = getDatasetSource(supportedByCurrentModel, supportedByCleanDataset);
  const group = inferBirdGroup(species);
  const overrides = profileOverrides[species] ?? {};

  return {
    species,
    scientificName: overrides.scientificName ?? toTitleCase(species),
    family: overrides.family ?? group.family,
    order: overrides.order ?? group.order,
    status: overrides.status ?? "Not listed",
    habitat: overrides.habitat ?? group.habitat,
    diet: overrides.diet ?? group.diet,
    size: overrides.size ?? "Varies by species",
    region: overrides.region ?? "Birds 525 training dataset",
    image: `/images/birds525/${slugify(species)}.jpg`,
    description:
      overrides.description ??
      `${toTitleCase(species)} is included as a ${source.toLowerCase()} class for image identification training.`,
    datasetSource: source,
    trainingImages: overrides.trainingImages ?? (supportedByCleanDataset ? 200 : 140),
    supportedByCurrentModel,
    supportedByCleanDataset,
  };
}

function getDatasetSource(currentModel: boolean, cleanDataset: boolean): BirdProfile["datasetSource"] {
  if (currentModel && cleanDataset) return "Current model + clean 50 dataset";
  if (cleanDataset) return "Clean 50 dataset";
  return "Current model";
}

function inferBirdGroup(species: string) {
  if (/(EAGLE|HAWK|OSPREY|MERLIN|KESTREL|CARACARA|VULTURE|CONDOR)/.test(species)) {
    return {
      family: "Raptors",
      order: "Accipitriformes / Falconiformes",
      habitat: "Open country, woodland edges, cliffs, wetlands, and other hunting areas.",
      diet: "Small mammals, birds, reptiles, fish, insects, or carrion depending on species.",
    };
  }
  if (/(DUCK|GOOSE|TEAL|WIGEON)/.test(species)) {
    return {
      family: "Waterfowl",
      order: "Anseriformes",
      habitat: "Lakes, marshes, rivers, ponds, and wetland edges.",
      diet: "Aquatic plants, seeds, insects, and small aquatic animals.",
    };
  }
  if (/(TERN|GULL|ALBATROSS|BOOBY|RAZORBILL|TROPICBIRD|OYSTER|KNOT|SPOONBILL|EGRET|HERON)/.test(species)) {
    return {
      family: "Waterbirds and seabirds",
      order: "Coastal and wetland birds",
      habitat: "Coasts, mudflats, wetlands, islands, and open water.",
      diet: "Fish, crustaceans, mollusks, insects, and other aquatic prey.",
    };
  }
  if (/(BARBET|BEE EATER|KINGFISHER|WOODPECKER|FLICKER|HORNBILL|BROADBILL|PITTA)/.test(species)) {
    return {
      family: "Forest birds",
      order: "Woodland specialist groups",
      habitat: "Forests, woodland edges, groves, and mature tree cover.",
      diet: "Insects, fruit, nectar, small animals, or seeds depending on species.",
    };
  }
  return {
    family: "Passerines and land birds",
    order: "Passeriformes / land bird groups",
    habitat: "Forest edges, fields, gardens, grasslands, or scrub depending on species.",
    diet: "Seeds, fruit, nectar, insects, or mixed small prey depending on species.",
  };
}

function toTitleCase(value: string) {
  return value
    .toLowerCase()
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function slugify(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

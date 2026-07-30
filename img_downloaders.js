(async () => {
  const { default: JSZip } = await import(
    "https://cdn.jsdelivr.net/npm/jszip@3.10.1/+esm"
  );

  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

  let previousCount = 0;
  let stableRounds = 0;

  while (stableRounds < 5) {
    window.scrollTo(0, document.documentElement.scrollHeight);
    await sleep(800);

    const count = [...document.images].filter(img =>
      (img.currentSrc || img.src).includes("/CardPreviews/")
    ).length;

    console.log(`${count} images de cartes actuellement chargées`);

    if (count === previousCount) {
      stableRounds++;
    } else {
      stableRounds = 0;
      previousCount = count;
    }
  }

  const imageUrls = [
    ...new Set(
      [...document.images]
        .map(img => img.currentSrc || img.src)
        .filter(url => url.includes("/CardPreviews/"))
    )
  ];

  if (!imageUrls.length) {
    throw new Error("Aucune image de carte trouvée.");
  }

  console.log(`${imageUrls.length} images vont être téléchargées.`);

  const zip = new JSZip();
  const manifest = [];

  for (let index = 0; index < imageUrls.length; index++) {
    const imageUrl = imageUrls[index];

    try {
      const response = await fetch(imageUrl);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const blob = await response.blob();

      const originalFilename =
        new URL(imageUrl).pathname.split("/").pop() ||
        `image-${index + 1}.webp`;

      const filename =
        `${String(index + 1).padStart(3, "0")}.webp`;

      zip.file(filename, blob);

      manifest.push({
        index: index + 1,
        filename,
        originalFilename,
        imageUrl
      });

      console.log(
        `[${index + 1}/${imageUrls.length}] ${filename}`
      );
    } catch (error) {
      console.error(`Échec pour ${imageUrl}`, error);
    }
  }

  zip.file(
    "images.json",
    JSON.stringify(manifest, null, 2)
  );

  console.log("Création du ZIP…");

  const zipBlob = await zip.generateAsync({
    type: "blob",
    compression: "DEFLATE",
    compressionOptions: {
      level: 6
    }
  });

  const downloadUrl = URL.createObjectURL(zipBlob);
  const link = document.createElement("a");

  link.href = downloadUrl;
  link.download = "pokemon-zone-set-images.zip";
  document.body.appendChild(link);
  link.click();
  link.remove();

  setTimeout(() => URL.revokeObjectURL(downloadUrl), 10_000);

  console.log(
    `Terminé : ${manifest.length} images ajoutées au ZIP.`
  );
})();